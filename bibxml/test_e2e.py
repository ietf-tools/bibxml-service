import os
from urllib.parse import quote_plus

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright


# https://github.com/microsoft/playwright-python/issues/439
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class MyViewTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def test_quick_search(self):
        page = self.browser.new_page()
        page.goto(self.live_server_url)
        page.fill('#quickSearchQuery', 'test')
        page.screenshot(path="test-artifacts/home.png")
        page.click('#quickSearchForm button[type=submit]')

        self.assertEquals(page.url, '%s%s' % (
            self.live_server_url,
            '/search/?query=test&allow_format_fallback=True&bypass_cache=True',
        ))

        page.close()


    def test_doi_ref_search(self):
        page = self.browser.new_page()
        page.goto(self.live_server_url)
        ref = "10.1093/benz/9780199773787.article.b00004912"
        page.fill('#doiRefToSearch', quote_plus(ref))
        page.screenshot(path="test-artifacts/doi_search.png")
        page.click('#doiRefSearchForm button[type=submit]')

        self.assertEquals(page.url, '%s%s' % (
            self.live_server_url,
            'get-one/external/doi/?ref=+https%3A%2F%2Fdoi.org%2F10.1093%2Fbenz%2F9780199773787.article.b00004912',
        ))

        page.close()
