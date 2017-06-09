import logging
import uuid
from time import sleep
from scrapy import Request, Selector
from scrapy.spiders import SitemapSpider
from selenium import webdriver
from selenium.common.exceptions import InvalidElementStateException

from thedigger.items import ProductDesc


class MySpider(SitemapSpider):
    name = "americanas"
    base_url = "http://www.americanas.com.br"

    sitemap_urls = [base_url + "/robots.txt"]

    # list all categories you wish to scrape
    sitemap_rules = [
        ('/categoria/eletrodomesticos/freezer/vertical', 'parse_category'),
        # ('/categoria/games/playstation-4/console-playstation-4', 'parse_category'),
        # ('/categoria/games/xbox-360/console-xbox-360', 'parse_category'),
    ]

    # list all postal codes you wish to calculate shipping price
    postal_codes = [
        "13083590",
        "24030077"
    ]

    def __init__(self, *args, **kwargs):
        # disable scrapy and selenium debug messages
        logger = logging.getLogger('scrapy')
        logger.setLevel(logging.ERROR)
        logger = logging.getLogger('selenium.webdriver')
        logger.setLevel(logging.ERROR)

        super(MySpider, self).__init__(*args, **kwargs)
        self.wd = None

    def closed(self, reason):
        if self.wd:
            self.wd.close()

    def parse_category(self, response):
        # get category
        category = response.url.split("categoria")[-1]
        # get number of items
        nitems = response.css("aside.sortbar div.form-group span::text").re(r"(\d+)")
        nitems = int(nitems[0]) if len(nitems) > 0 else 0

        self.log("Found {} items in category '{}'".format(nitems, category))

        # seems to be hardcoded in pages
        limit = 24
        # initial offset
        offset = 0
        # parameters format string
        params = "?limite={}&offset={}"

        # iterate category pages
        while offset < nitems:
            url = response.url + params.format(limit, offset)
            yield Request(url, callback=self.parse_category_pages)
            offset += limit

    def parse_category_pages(self, response):
        # get items urls
        urls = response.css("section.card-product a.card-product-url::attr(href)").re(r"(.+)\?")

        if len(urls) == 0:
            self.logger.warning("Category empty ({})!".format(response.url))
            return

        for url in urls:
            req = Request(self.base_url + url, self.parse_item)
            req.meta["category"] = response.url.split("/categoria/")[-1].split("/")[0]
            yield req

    def parse_item(self, response):
        variations = []
        if len(response.css("section.card-variations")) > 0:
            vtype = response.css("section.card-variations li.variations-item::attr(data-type)").extract_first()
            if vtype == u"Voltagem":
                for v in ["110", "220"]:
                    variations.append({
                        # must add some random data to be able to fetch
                        "href": "/{}?voltagem={}+volts".format(uuid.uuid4().get_hex(), v),
                        "title": "{}v".format(v),
                    })
            else:
                self.logger.warning(u"Variation '{}' not implemented ({})!".format(vtype, response.url))
                return

        name = response.css("section.card-title h1::text").extract_first()
        iid = response.css("span.product-id::text").re(r"(\d+)")
        if len(iid) == 0:
            self.logger.warning("No ID found ({})!".format(response.url))
            return
        iid = iid[0]

        item = ProductDesc(
            name=name,
            itemId=iid,
            url=response.url,
            price={}
        )
        item["category"] = response.meta["category"]

        self.log(u"Parsing item '{}':".format(item["name"]))
        self.log(u"\tItemID:     {}".format(item["itemId"]))
        self.log(u"\turl:        {}".format(response.url))

        if not variations:
            item["price"]["unique"] = self._get_price(response)
            yield item
        else:
            yield self._next_variation(item, variations)

    def parse_item_variation(self, response):
        item = response.meta["item"]
        variations = response.meta["variations"]
        cur_variation = response.meta["cur_variation"]

        item["price"][cur_variation] = self._get_price(response)

        if variations:
            yield self._next_variation(item, variations)
        else:
            yield item

    def _get_price(self, response):
        price = response.css("p.sales-price::text").extract_first()
        shipping = self._get_shipping(response)

        return {
            "product": price.encode("ascii", "ignore") if price else "none",
            "shipping": shipping
        }

    def _get_shipping(self, response):
        if len(self.postal_codes) == 0:
            # no shipping codes available
            return {}

        shipping = {}
        wd = self._get_webdriver()

        wd.get(response.url)

        try:
            form = wd.find_element_by_id("input-freight-product")
            ok = wd.find_element_by_id("bt-freight-product")
        except:
            self.logger.warning("No option to calculate shipping ({})!".format(response.url))
            return {}

        for cep in self.postal_codes:
            retries = 3

            while retries:
                try:
                    form.clear()
                    form.send_keys(cep)
                    ok.click()
                    break
                except InvalidElementStateException:
                    retries -= 1
                finally:
                    sleep(0.3)

            if not retries:
                self.logger.warning("Couldn't calculate shipping ({})!".format(response.url))
                return {}

            # get source from selenium and create new scrapy selector
            source = wd.page_source
            sel = Selector(text=source)

            rows = sel.css("table.table-freight tbody tr")
            shipping[cep] = []
            for row in rows:
                data = row.css("td::text").extract()
                shipping[cep].append({
                    "type": data[0],
                    "price": data[1],
                    "date": data[2],
                })

        return shipping

    def _get_webdriver(self):
        if not self.wd:
            options = webdriver.ChromeOptions()

            # point to appropriate chrome binary
            # options.binary_location = 'path/to/bin/chrome'

            # uncomment if you have Chrome version > 59 (windows - version > 60) to enable headless scraping
            # options.add_argument('headless')

            # disable cache
            options.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2})

            self.wd = webdriver.Chrome(chrome_options=options)

        return self.wd

    def _next_variation(self, item, variations):
        req = Request(item["url"] + variations[0]["href"], self.parse_item_variation)
        req.meta["item"] = item
        req.meta["variations"] = variations[1:]
        req.meta["cur_variation"] = variations[0]["title"]
        return req
