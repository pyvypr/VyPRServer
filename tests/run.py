from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver import ActionChains
from selenium.webdriver.firefox.options import Options

import unittest

#data dependent on the database
#default_tab = "client"
default_tab = "server"
other_tab = "server"
no_of_tabs = 1
no_of_functions = 2
first_code_length = 33
other_code_length = 95
first_f_calls = 4000 + 2
other_f_calls = 3910 + 2
higlighted_line_index = 251-241
binding_line_index = 251-241
not_binding_line_index = 260-241


def check_if_exists(element, tag_name):
    try:
        element.find_element_by_tag_name(tag_name)
        return True
    except:
        return False

def simulate_tab_click(driver):
    #simulate clicking on a non-default tab
    tabs = WebDriverWait(driver, 10).until(lambda d: d.find_elements_by_class_name("tablinks"))
    for tab in tabs:
        if tab.text == other_tab:
            element = tab
    ActionChains(driver).click(element).perform()

def simulate_specification_selection(driver, n):
    # find the specification buttons
    content_list = driver.find_elements_by_class_name("tabcontent")
    for c in content_list:
        if c.get_attribute("id") == ("tab-"+other_tab): content = c
    buttons = content.find_elements_by_tag_name("button")
    #click on the n-th specification
    ActionChains(driver).click(buttons[n]).perform()

class TestBaseFirefox(unittest.TestCase):

    def setUp(self):
        options = Options()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)

    def tearDown(self):
        self.driver.close()


class LoadingTest(TestBaseFirefox):

    def test_main_page(self):
        driver = self.driver
        driver.get("http://localhost:9002/")

        #check that tab buttons are displayed
        el = driver.find_element(By.ID, "function-list")
        tabs = WebDriverWait(el, 10).until(lambda d: d.find_elements_by_class_name("tablinks"))
        assert len(tabs) == no_of_tabs
        assert tabs[0].text == default_tab

        #check that the content of the tab selected by default is displayed, and others not
        content_list = el.find_elements_by_class_name("tabcontent")
        for c in content_list:
            if c.get_attribute("id") == ("tab-"+default_tab):
                content = c
            else:
                assert c.get_attribute("style") == "display: none;"
        self.assertEqual(content.get_attribute("style"), "")

        #check that there is a specification displayed within the selected content
        assert check_if_exists(content, "button")
        specification = content.find_element_by_tag_name("button")
        assert check_if_exists(specification, "p")


class TabTest(TestBaseFirefox):

    def test_choosing_tab(self):
        driver = self.driver
        driver.get("http://localhost:9002/")

        simulate_tab_click(driver)

        # check that the right tabcontent is displayed
        content_list = driver.find_elements_by_class_name("tabcontent")
        for c in content_list:
            if c.get_attribute("id") == ("tab-"+other_tab):
                content = c
            else:
                assert c.get_attribute("style") == "display: none;"
        assert "display: none" not in content.get_attribute("style")


class FunctionSelectTest(TestBaseFirefox):

    def test_choosing_function(self):
        driver = self.driver
        driver.get("http://localhost:9002/")

        simulate_tab_click(driver)

        # find the specification buttons
        content_list = driver.find_elements_by_class_name("tabcontent")
        for c in content_list:
            if c.get_attribute("id") == ("tab-"+other_tab): content = c
        buttons = content.find_elements_by_tag_name("button")
        assert len(buttons) == no_of_functions

        #click on the first specification, check that calls are loaded and source code displayed
        ActionChains(driver).click(buttons[0]).perform()
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("function-list").get_attribute("style") == "display: none;")
        assert driver.find_element_by_id("function-list").get_attribute("style") == "display: none;"

        calls_list = driver.find_element_by_id("function-call-list")
        calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
        assert len(calls)==(first_f_calls)

        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
        code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
        lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
        assert len(lines)==first_code_length

        #now we want to test the other function if it exists
        if (len(buttons)>1):
            ActionChains(driver).click(driver.find_element_by_id("function-title")).perform()
            self.assertEqual(driver.find_element_by_id("function-list").get_attribute("style"), "")
            ActionChains(driver).click(buttons[1]).perform()
            calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
            assert len(calls)==(other_f_calls)

            WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
            code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
            lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
            assert len(lines)==other_code_length

        #TODO check colouring


class CallsSelectTest(TestBaseFirefox):

    def test_selecting_calls(self):
        driver = self.driver
        driver.get("http://localhost:9002/")

        simulate_tab_click(driver)

        simulate_specification_selection(driver, 0)

        #wait for the calls and code to load
        calls_list = driver.find_element_by_id("function-call-list")
        calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
        code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
        lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))

        #select a call and check that the code reacts to this
        # some code lines are hidden, some are highlighted and should have binding buttons
        ActionChains(driver).click(calls[2].find_element_by_tag_name("input")).perform()
        WebDriverWait(driver, 50).until(lambda d:"display: none" in lines[higlighted_line_index-4].get_attribute("style"))
        assert lines[0].get_attribute("style") == "background-color: transparent;"
        assert "display: none" in lines[higlighted_line_index-4].get_attribute("style")
        assert "display: none" not in lines[higlighted_line_index].get_attribute("style")
        assert "transparent" not in lines[higlighted_line_index].get_attribute("style")
        assert check_if_exists(lines[binding_line_index], "button")
        assert check_if_exists(lines[not_binding_line_index], "button")==False


if __name__ == "__main__":
    unittest.main()
