# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os
from scrapy.exporters import JsonItemExporter
from scrapy.exceptions import DropItem


class JsonWriterPipeline(object):
    # path to dump json files
    path = "dump"

    def __init__(self):
        self.exporters = {}
        self.ids = set()

    def open_spider(self, spider):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def close_spider(self, spider):
        for _, exp in self.exporters.items():
            exp["exporter"].finish_exporting()
            exp["file"].close()

    def process_item(self, item, spider):
        cat = item["category"]
        iid = item["itemId"]
        exp = self._get_create_file_exporter(spider, cat)

        if iid in self.ids:
            raise DropItem("ID %d already dumped." % iid)

        self.ids.add(iid)
        exp.export_item(item)

        return item

    def _get_create_file_exporter(self, spider, category):
        if category not in self.exporters:
            fn = spider.name + "_" + category + ".json"
            fd = open(os.path.join(self.path, fn), "w+")
            exporter = JsonItemExporter(fd,
                                        fields_to_export=["name", "itemId", "url", "price"],
                                        indent=2,
                                        encoding="utf-8")
            exporter.start_exporting()

            self.exporters[category] = {
                "file": fd,
                "exporter": exporter
            }

        return self.exporters[category]["exporter"]
