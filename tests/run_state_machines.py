"""
Test module for state_machine_testing library.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import state_machine_testing as smt


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

"""
Testing utility functions
"""


def check_if_exists(element, tag_name):
    try:
        element.find_element_by_tag_name(tag_name)
        return True
    except:
        return False


def simulate_tab_click(driver):
    # simulate clicking on a non-default tab
    tabs = WebDriverWait(driver, 10).until(lambda d: d.find_elements_by_class_name("tablinks"))
    element = tabs[0]
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
    # click on the n-th specification
    ActionChains(driver).click(buttons[n]).perform()


"""
State Machine functions
"""


# entry point
def load_main_page(runner):
    runner.driver().get("http://localhost:9002/")


def assert_first_screen(runner):
    # check that tab buttons are displayed
    driver = runner.driver()
    el = driver.find_element(By.ID, "function-list")
    tabs = WebDriverWait(el, 10).until(lambda d: d.find_elements_by_class_name("tablinks"))
    assert len(tabs) == no_of_tabs
    #assert tabs[0].text == default_tab

    # check that the content of the tab selected by default is displayed, and others not
    content_list = el.find_elements_by_class_name("tabcontent")
    for c in content_list:
        if c.get_attribute("id") == ("tab-" + default_tab):
            content = c
        else:
            assert c.get_attribute("style") == "display: none;"
    assert content.get_attribute("style") == ""

    # check that there is a specification displayed within the selected content
    assert check_if_exists(content, "button")
    specification = content.find_element_by_tag_name("button")
    assert check_if_exists(specification, "p")


# after load_main_page
def choose_tab(runner):
    driver = runner.driver()
    simulate_tab_click(driver)


def assert_tab_selection(runner):
    driver = runner.driver()
    # check that the right tabcontent is displayed
    content_list = driver.find_elements_by_class_name("tabcontent")
    for c in content_list:
        if c.get_attribute("id") == ("tab-" + other_tab):
            content = c
        else:
            assert c.get_attribute("style") == "display: none;"
    assert "display: none" not in content.get_attribute("style")
    buttons = content.find_elements_by_tag_name("button")
    assert len(buttons) == no_of_functions

    # store 'buttons' globally
    runner.store().put("buttons", buttons)


# after choose_tab
def choose_specification(runner):
    driver = runner.driver()
    # get the value of buttons from the global store
    buttons = runner.store().get("buttons")
    # perform a click
    ActionChains(driver).click(buttons[0]).perform()


def assert_specification_selection(runner):
    driver = runner.driver()
    WebDriverWait(driver, 10).until(
        lambda d: d.find_element_by_id("function-list").get_attribute("height") == 0)
    print(driver.find_element_by_id("function-list").get_attribute("height"))
    assert driver.find_element_by_id("function-list").get_attribute("style") == "height: 0;"

    calls_list = driver.find_element_by_id("function-call-list")
    calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
    assert len(calls) == first_f_calls

    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
    code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
    lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
    assert len(lines) == first_code_length


# after choose_specification
def choose_call(runner):
    driver = runner.driver()
    # wait for the calls and code to load
    calls_list = driver.find_element_by_id("function-call-list")
    calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
    code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
    lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))

    # store some variables globally
    runner.store().put("lines", lines)
    runner.store().put("calls_list", calls_list)

    # select a call and check that the code reacts to this
    # some code lines are hidden, some are highlighted and should have binding buttons
    ActionChains(driver).click(calls[2].find_element_by_tag_name("input")).perform()


def assert_call_selection(runner):
    driver = runner.driver()

    # get the value of lines from the global store
    lines = runner.store().get("lines")

    WebDriverWait(driver, 50).until(
        lambda d: "display: none" in lines[higlighted_line_index - 4].get_attribute("style"))

    assert lines[0].get_attribute("style") == "background-color: transparent;"
    assert "display: none" in lines[higlighted_line_index - 4].get_attribute("style")
    assert "display: none" not in lines[higlighted_line_index].get_attribute("style")
    assert "transparent" not in lines[higlighted_line_index].get_attribute("style")
    assert check_if_exists(lines[binding_line_index], "button")
    assert not check_if_exists(lines[not_binding_line_index], "button")


# after choose_call
def choose_binding(runner):
    driver = runner.driver()
    lines = runner.store().get("lines")

    # click a binding
    ActionChains(driver).click(lines[higlighted_line_index].find_element_by_tag_name("button")).perform()


def assert_binding_selection(runner):
    driver = runner.driver()
    lines = runner.store().get("lines")

    assert "font-weight: bold" in lines[higlighted_line_index].find_element_by_tag_name("button").get_attribute("style")


# after choose_binding
def choose_sub_atom(runner):
    driver = runner.driver()

    ActionChains(driver).click(driver.find_elements_by_class_name("subatom-clickable")[0]).perform()


def assert_sub_atom_selection(runner):
    driver = runner.driver()

    assert driver.find_elements_by_class_name("subatom-clickable-active")[0].get_attribute("subatom-index") == "0"


# after choose_binding
def choose_dropdown_menu_option(runner):
    driver = runner.driver()

    ActionChains(driver).click(driver.find_elements_by_class_name("dropdown-menu-option")[0]).perform()


def assert_dropdown_menu_click_result(runner):
    driver = runner.driver()

    WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.CLASS_NAME, "nvd3-svg"))
    )
    assert "height" in driver.find_elements_by_class_name("nvd3-svg")[0].get_attribute("style")


# after choose_dropdown_menu_option
# this should loop back to before the plot was opened
def close_plot(runner):
    driver = runner.driver()

    ActionChains(driver).click(driver.find_elements_by_class_name("close-plot")[0]).perform()


# after choose_call
def open_function_panel(runner):
    driver = runner.driver()
    ActionChains(driver).click(driver.find_element_by_id("function-title")).perform()


def assert_open_function_panel(runner):
    driver = runner.driver()
    assert driver.find_element_by_id("function-list").get_attribute("style") == ""


# after open_function_panel
def choose_other_function(runner):
    driver = runner.driver()
    # get the 'buttons' variable from the global store
    buttons = runner.store().get("buttons")
    # send the click event
    ActionChains(driver).click(buttons[1]).perform()


def assert_other_function_selection(runner):
    driver = runner.driver()
    calls_list = runner.store().get("calls_list")

    calls = WebDriverWait(calls_list, 10).until(lambda d: d.find_elements_by_class_name("list-group-item"))
    assert len(calls) == other_f_calls

    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
    code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
    lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
    assert len(lines) == other_code_length


if __name__ == "__main__":

    # set up state machine
    state_machine = smt.StateMachine()

    t1 = state_machine.add_transition(load_main_page)
    s1 = t1.set_target_state(assert_first_screen)

    t2 = s1.add_outgoing_transition(choose_tab)
    s2 = t2.set_target_state(assert_tab_selection)

    t3 = s2.add_outgoing_transition(choose_specification)
    s3 = t3.set_target_state(assert_specification_selection)

    t4 = s3.add_outgoing_transition(choose_call)
    s4 = t4.set_target_state(assert_call_selection)

    t4_1 = s4.add_outgoing_transition(choose_binding)
    s4_1 = t4_1.set_target_state(assert_binding_selection)

    t4_2 = s4_1.add_outgoing_transition(choose_sub_atom)
    s4_2 = t4_2.set_target_state(assert_sub_atom_selection)

    t4_3 = s4_2.add_outgoing_transition(choose_dropdown_menu_option)
    s4_3 = t4_3.set_target_state(assert_dropdown_menu_click_result)

    # add loop
    state_machine.add_transition(close_plot, source_state=s4_3, target_state=s4_2)


    t5 = s4.add_outgoing_transition(
        open_function_panel,
        guard=lambda runner : len(runner.store().get("buttons")) > 1
    )
    s5 = t5.set_target_state(assert_open_function_panel)

    t6 = s5.add_outgoing_transition(choose_other_function)
    s6 = t6.set_target_state(assert_other_function_selection)

    state_machine.write_to_file("state-machine.gv")

    state_machine.run()

    state_machine.write_to_file("state-machine-with-results.gv")
