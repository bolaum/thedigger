# thedigger

A data scraper for [americanas.com.br](http://www.americanas.com.br/) using [Scrapy](https://scrapy.org/) and [Selenium](http://selenium-python.readthedocs.io/).

Last tested on 2017-06-09.

## Features

* Scraping by categories
* Get product names, IDs, urls and price
* Support for item variations in voltage (220v / 110v) (**will skip items with any other kind of selection (i.e. color)**)
* UTF-8 json dump of items by category
* Calculates shipping for each item for a list of postal codes (brazilian CEP)

## Dependencies

* Scrapy (https://docs.scrapy.org/en/latest/intro/install.html)
* Selenium (http://selenium-python.readthedocs.io/installation.html)

## Usage

Checkout the repository:

```bash
git clone https://github.com/bolaum/thedigger.git
cd thedigger/
```

And install dependencies (virtualenv recommended):

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

Or if using conda:

```bash
conda create -n thedigger --file requirements.txt -c conda-forge
source activate thedigger
```

#### Select categories

Add regular expression of categories to scrape in `thedigger/spiders/americanas.py`:

```python
class MySpider(SitemapSpider):
    ...        
    # list all categories you wish to scrape
    sitemap_rules = [
        ('/categoria/eletrodomesticos/freezer/vertical', 'parse_category'),
        # ('/categoria/games/playstation-4/console-playstation-4', 'parse_category'),
        # ('/categoria/games/xbox-360/console-xbox-360', 'parse_category'),
    ]    
    ...    
```

#### Add postal codes to calculate shipping

Add brazilian postal codes to calculate shipping for each item in `thedigger/spiders/americanas.py`:

```python
class MySpider(SitemapSpider):
    ...        
    # list all postal codes you wish to calculate shipping price
    postal_codes = [
        "13083590",
        "24030077"
    ]    
    ...    
```

Calculating shipping costs uses Selenium to fill in forms and will be slow. If you don't need it, make it empty for faster scraping.

#### Running

Just start the crawler with

```bash
scrapy crawl americanas
```

## Output
It will output one json file for each category to `./dump/` directory by default. This can be changed in `thedigger/pipelines.py`, attribute `path`of `JsonWriterPipeline`:

```python
class JsonWriterPipeline(object):
    # path to dump json files
    path = "dump"
    ...
```

Output example:
```json
[
{
  "itemId": "21318848", 
  "url": "http://www.americanas.com.br/produto/21318848", 
  "price": {
    "unique": {
      "product": "R$ 3.624,96", 
      "shipping": {
        "24030077": [
          {
            "date": "15 dias úteis", 
            "price": "R$ 219,89", 
            "type": "Econômica"
          }
        ], 
        "13083590": []
      }
    }
  }, 
  "name": "Freezer Horizontal 311 L Congelador Com Tampa De Vidro Fricon 127 V"
},
{
  "itemId": "117247630", 
  "url": "http://www.americanas.com.br/produto/117247630", 
  "price": {
    "110v": {
      "product": "R$ 2.499,99", 
      "shipping": {
        "24030077": [
          {
            "date": "5 dias úteis", 
            "price": "R$ 49,99", 
            "type": "Rápida"
          }, 
          {
            "date": "6 dias úteis", 
            "price": "R$ 24,99", 
            "type": "Econômica"
          }
        ], 
        "13083590": [
          {
            "date": "5 dias úteis", 
            "price": "R$ 49,99", 
            "type": "Rápida"
          }, 
          {
            "date": "7 dias úteis", 
            "price": "R$ 24,99", 
            "type": "Econômica"
          }, 
          {
            "date": "A agendar", 
            "price": "R$ 24,99", 
            "type": "Agendada"
          }
        ]
      }
    }, 
    "220v": {
      "product": "R$ 2.629,57", 
      "shipping": {
        "24030077": [], 
        "13083590": []
      }
    }
  }, 
  "name": "Freezer Vertical Brastemp BVR28 228 Litros Inox Frost Free"
}
]
```
