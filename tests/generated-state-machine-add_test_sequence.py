
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

import state_machine_testing as smt


#data dependent on the database
default_tab = "server"
other_tab = "server"
no_of_tabs = 1
no_of_functions = 2
first_code_length = 34
other_code_length = 96
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


# transition code

def transition_function_page_load(runner):
  runner.driver().get("http://localhost:9002/")

def transition_function_1(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=3]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=3]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_2(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=4]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=4]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_3(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=12]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_4(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_5(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=22]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_6(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=22]/*[position()=6]/*[position()=3]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_7(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=3]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=3]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_8(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=4]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=4]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_9(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=1]/*[position()=4]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=5]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_10(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=13]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_11(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=1]/*[position()=3]/*[position()=3]/*[position()=1]/*[position()=1]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_12(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=14]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_13(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=14]/*[position()=6]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_14(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=76]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_15(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=76]/*[position()=6]/*[position()=3]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_16(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=13]/*[position()=3]/*[position()=2]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_17(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=2]/*[position()=1]/*[position()=3]/*[position()=3]/*[position()=1]/*[position()=1]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_18(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=14]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_19(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=14]/*[position()=6]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_20(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=89]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_21(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=89]/*[position()=6]/*[position()=3]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


def transition_function_22(runner):
  driver = runner.driver()
  locator = (By.XPATH, '/html/body/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=1]/*[position()=1]/*[position()=2]/*[position()=3]/*[position()=20]/*[position()=3]/*[position()=1]')
  wait = WebDriverWait(driver, 10)
  element = wait.until(EC.presence_of_element_located(locator))
  time.sleep(5)
  element.click()


# state code

def state_function_page_loaded(runner):
  driver = runner.driver()

  #check that tab buttons are displayed
  el = driver.find_element(By.ID, "function-list")
  tabs = WebDriverWait(el, 10).until(lambda d: d.find_elements_by_class_name("tablinks"))
  assert len(tabs) == no_of_tabs

  #check that the content of the tab selected by default is displayed, and others not
  content_list = el.find_elements_by_class_name("tabcontent")
  for c in content_list:
      if c.get_attribute("id") == ("tab-"+default_tab):
          content = c
      else:
          assert c.get_attribute("style") == "display: none;"
  assert content.get_attribute("style") == ""

  #check that there is a specification displayed within the selected content
  assert check_if_exists(content, "button")
  specification = content.find_element_by_tag_name("button")
  assert check_if_exists(specification, "p")
  buttons = content.find_elements_by_tag_name("button")
  assert len(buttons) == no_of_functions

def state_function_after_transition_1(runner):
  driver = runner.driver()

  calls_list = driver.find_element_by_id("function-call-list")
  calls = WebDriverWait(calls_list, 20).until(lambda d: d.find_elements_by_class_name("list-group-item"))
  assert len(calls)==(first_f_calls)

  WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
  code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
  lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
  assert len(lines)==first_code_length

def state_function_after_transition_2(runner):
  driver = runner.driver()
  lines = WebDriverWait(driver, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
  assert lines[0].get_attribute("style") == "background-color: transparent;"
  assert "display: none" in lines[higlighted_line_index-4].get_attribute("style")
  assert "display: none" not in lines[higlighted_line_index].get_attribute("style")
  assert "transparent" not in lines[higlighted_line_index].get_attribute("style")
  assert check_if_exists(lines[binding_line_index], "button")
  assert check_if_exists(lines[not_binding_line_index], "button")==False

def state_function_after_transition_3(runner):
  driver = runner.driver()
  binding = driver.find_elements_by_class_name("code_listing_line")[binding_line_index].find_element_by_tag_name("button")
  assert "bold" in binding.get_attribute("style")
  subatom_list = driver.find_element_by_id("specification_listing").find_elements_by_class_name("subatom-clickable")
  assert len(subatom_list) == 1

def state_function_after_transition_4(runner):
  driver = runner.driver()
  options = driver.find_elements_by_class_name("code_listing_line")[not_binding_line_index].find_elements_by_class_name("options")
  assert len(options) == 1

def state_function_after_transition_5(runner):
  driver = runner.driver()
  line = driver.find_elements_by_class_name("code_listing_line")[not_binding_line_index]
  dropdown = line.find_element_by_class_name("dropdown-content")
  assert "display: block" in dropdown.get_attribute("style")
  options = dropdown.find_elements_by_class_name("dropdown-menu-option")
  assert len(options) == 3

def state_function_after_transition_6(runner):
    driver = runner.driver()
    alerts = driver.find_elements_by_class_name("alert-info")
    lines = driver.find_elements_by_class_name("code_listing_line")
    assert len(alerts) == 1
    assert "display: none" not in lines[higlighted_line_index-4].get_attribute("style")

def state_function_after_transition_7(runner):
  driver = runner.driver()

  calls_list = driver.find_element_by_id("function-call-list")
  calls = WebDriverWait(calls_list, 20).until(lambda d: d.find_elements_by_class_name("list-group-item"))
  assert len(calls)==(other_f_calls)

  WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("specification_listing"))
  code = WebDriverWait(driver, 50).until(lambda d: d.find_element_by_class_name("code_listing"))
  lines = WebDriverWait(code, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
  assert len(lines)==other_code_length

def state_function_after_transition_8(runner):
  driver = runner.driver()
  lines = WebDriverWait(driver, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
  assert lines[0].get_attribute("style") == "background-color: transparent;"
  assert "display: none" in lines[2].get_attribute("style")
  assert "display: none" in lines[73].get_attribute("style")
  assert "display: none" not in lines[11].get_attribute("style")
  assert "transparent" not in lines[11].get_attribute("style")
  assert check_if_exists(lines[11], "button")
  assert check_if_exists(lines[12], "button")==False

def state_function_after_transition_9(runner):
  driver = runner.driver()
  lines = WebDriverWait(driver, 50).until(lambda d: d.find_elements_by_class_name("code_listing_line"))
  assert lines[0].get_attribute("style") == "background-color: transparent;"
  assert "display: none" in lines[2].get_attribute("style")
  assert "display: none" not in lines[73].get_attribute("style")
  assert "display: none" not in lines[11].get_attribute("style")
  assert "transparent" not in lines[11].get_attribute("style")
  assert check_if_exists(lines[73], "button")
  assert check_if_exists(lines[74], "button")==False

def state_function_after_transition_10(runner):
  driver = runner.driver()
  binding = driver.find_elements_by_class_name("code_listing_line")[73].find_element_by_tag_name("button")
  bindings = driver.find_elements_by_class_name("code_listing_line")[11].find_elements_by_tag_name("button")
  assert "bold" in binding.get_attribute("style")
  assert "bold" in bindings[0].get_attribute("style")
  assert "bold" not in bindings[1].get_attribute("style")
  subatom_list = driver.find_element_by_id("specification_listing").find_elements_by_class_name("subatom-clickable")
  assert len(subatom_list) == 2

def state_function_after_transition_11(runner):
  driver = runner.driver()
  options = driver.find_elements_by_class_name("code_listing_line")[11].find_elements_by_class_name("options")
  assert len(options) == 1

def state_function_after_transition_12(runner):
  driver = runner.driver()
  line = driver.find_elements_by_class_name("code_listing_line")[11]
  dropdown = line.find_element_by_class_name("dropdown-content")
  assert "display: block" in dropdown.get_attribute("style")
  options = dropdown.find_elements_by_class_name("dropdown-menu-option")
  assert len(options) == 1

def state_function_after_transition_13(runner):
  driver = runner.driver()
  options = driver.find_elements_by_class_name("code_listing_line")[73].find_elements_by_class_name("options")
  assert len(options) == 1

def state_function_after_transition_14(runner):
  driver = runner.driver()
  line = driver.find_elements_by_class_name("code_listing_line")[73]
  dropdown = line.find_element_by_class_name("dropdown-content")
  assert "display: block" in dropdown.get_attribute("style")
  options = dropdown.find_elements_by_class_name("dropdown-menu-option")
  assert len(options) == 3

def state_function_after_transition_15(runner):
    driver = runner.driver()
    alerts = driver.find_elements_by_class_name("alert-info")
    assert len(alerts) == 1

def state_function_after_transition_16(runner):
  driver = runner.driver()
  binding = driver.find_elements_by_class_name("code_listing_line")[86].find_element_by_tag_name("button")
  bindings = driver.find_elements_by_class_name("code_listing_line")[11].find_elements_by_tag_name("button")
  assert "bold" in binding.get_attribute("style")
  assert "bold" not in bindings[0].get_attribute("style")
  assert "bold" in bindings[1].get_attribute("style")
  subatom_list = driver.find_element_by_id("specification_listing").find_elements_by_class_name("subatom-clickable")
  assert len(subatom_list) == 2

def state_function_after_transition_17(runner):
  driver = runner.driver()
  options = driver.find_elements_by_class_name("code_listing_line")[11].find_elements_by_class_name("options")
  assert len(options) == 1

def state_function_after_transition_18(runner):
  driver = runner.driver()
  line = driver.find_elements_by_class_name("code_listing_line")[11]
  dropdown = line.find_element_by_class_name("dropdown-content")
  assert "display: block" in dropdown.get_attribute("style")
  options = dropdown.find_elements_by_class_name("dropdown-menu-option")
  assert len(options) == 1

def state_function_after_transition_19(runner):
  driver = runner.driver()
  options = driver.find_elements_by_class_name("code_listing_line")[86].find_elements_by_class_name("options")
  assert len(options) == 1

def state_function_after_transition_20(runner):
  driver = runner.driver()
  line = driver.find_elements_by_class_name("code_listing_line")[86]
  dropdown = line.find_element_by_class_name("dropdown-content")
  assert "display: block" in dropdown.get_attribute("style")
  options = dropdown.find_elements_by_class_name("dropdown-menu-option")
  assert len(options) == 3

def state_function_after_transition_21(runner):
  driver = runner.driver()

  code = driver.find_elements_by_class_name("code_listing_line")
  options = code[17].find_elements_by_class_name("options")
  assert len(options) == 1
  for i in range(18, 43):
      assert "background: transparent" not in code[i].get_attribute("style")
  for i in range(57, 85):
      assert "background: transparent" not in code[i].get_attribute("style")

def state_function_after_transition_22(runner):
    driver = runner.driver()
    line = driver.find_elements_by_class_name("code_listing_line")[17]
    dropdown = line.find_element_by_class_name("dropdown-content")
    assert "display: block" in dropdown.get_attribute("style")
    options = dropdown.find_elements_by_class_name("dropdown-menu-option")
    assert len(options) == 2


# state machine code

# initial instantiation

state_machine = smt.StateMachine()
initial_state = state_machine._start_state
state_object_after_transition_0 = smt.StateMachineState(state_function_page_loaded)
transition_object_page_load = smt.StateMachineTransition(initial_state, transition_function_page_load, state_object_after_transition_0)
initial_state.add_outgoing_transition(transition_object_page_load)

# states

state_object_after_transition_1 = smt.StateMachineState(state_function_after_transition_1)
state_object_after_transition_2 = smt.StateMachineState(state_function_after_transition_2)
state_object_after_transition_3 = smt.StateMachineState(state_function_after_transition_3)
state_object_after_transition_4 = smt.StateMachineState(state_function_after_transition_4)
state_object_after_transition_5 = smt.StateMachineState(state_function_after_transition_5)
state_object_after_transition_6 = smt.StateMachineState(state_function_after_transition_6)
state_object_after_transition_7 = smt.StateMachineState(state_function_after_transition_7)
state_object_after_transition_8 = smt.StateMachineState(state_function_after_transition_8)
state_object_after_transition_9 = smt.StateMachineState(state_function_after_transition_9)
state_object_after_transition_10 = smt.StateMachineState(state_function_after_transition_10)
state_object_after_transition_11 = smt.StateMachineState(state_function_after_transition_11)
state_object_after_transition_12 = smt.StateMachineState(state_function_after_transition_12)
state_object_after_transition_13 = smt.StateMachineState(state_function_after_transition_13)
state_object_after_transition_14 = smt.StateMachineState(state_function_after_transition_14)
state_object_after_transition_15 = smt.StateMachineState(state_function_after_transition_15)
state_object_after_transition_16 = smt.StateMachineState(state_function_after_transition_16)
state_object_after_transition_17 = smt.StateMachineState(state_function_after_transition_17)
state_object_after_transition_18 = smt.StateMachineState(state_function_after_transition_18)
state_object_after_transition_19 = smt.StateMachineState(state_function_after_transition_19)
state_object_after_transition_20 = smt.StateMachineState(state_function_after_transition_20)
state_object_after_transition_21 = smt.StateMachineState(state_function_after_transition_21)
state_object_after_transition_22 = smt.StateMachineState(state_function_after_transition_22)

# transitions

transition_object_1 = smt.StateMachineTransition(state_object_after_transition_0, transition_function_1, state_object_after_transition_1)
state_object_after_transition_0.add_outgoing_transition(transition_object_1)
transition_object_2 = smt.StateMachineTransition(state_object_after_transition_1, transition_function_2, state_object_after_transition_2)
state_object_after_transition_1.add_outgoing_transition(transition_object_2)
transition_object_3 = smt.StateMachineTransition(state_object_after_transition_2, transition_function_3, state_object_after_transition_3)
state_object_after_transition_2.add_outgoing_transition(transition_object_3)
transition_object_4 = smt.StateMachineTransition(state_object_after_transition_3, transition_function_4, state_object_after_transition_4)
state_object_after_transition_3.add_outgoing_transition(transition_object_4)
transition_object_5 = smt.StateMachineTransition(state_object_after_transition_4, transition_function_5, state_object_after_transition_5)
state_object_after_transition_4.add_outgoing_transition(transition_object_5)
transition_object_6 = smt.StateMachineTransition(state_object_after_transition_5, transition_function_6, state_object_after_transition_6)
state_object_after_transition_5.add_outgoing_transition(transition_object_6)
transition_object_7 = smt.StateMachineTransition(state_object_after_transition_0, transition_function_7, state_object_after_transition_7)
state_object_after_transition_0.add_outgoing_transition(transition_object_7)
transition_object_8 = smt.StateMachineTransition(state_object_after_transition_7, transition_function_8, state_object_after_transition_8)
state_object_after_transition_7.add_outgoing_transition(transition_object_8)
transition_object_9 = smt.StateMachineTransition(state_object_after_transition_8, transition_function_9, state_object_after_transition_9)
state_object_after_transition_8.add_outgoing_transition(transition_object_9)
transition_object_10 = smt.StateMachineTransition(state_object_after_transition_9, transition_function_10, state_object_after_transition_10)
state_object_after_transition_9.add_outgoing_transition(transition_object_10)
transition_object_11 = smt.StateMachineTransition(state_object_after_transition_10, transition_function_11, state_object_after_transition_11)
state_object_after_transition_10.add_outgoing_transition(transition_object_11)
transition_object_12 = smt.StateMachineTransition(state_object_after_transition_11, transition_function_12, state_object_after_transition_12)
state_object_after_transition_11.add_outgoing_transition(transition_object_12)
transition_object_13 = smt.StateMachineTransition(state_object_after_transition_12, transition_function_13, state_object_after_transition_13)
state_object_after_transition_12.add_outgoing_transition(transition_object_13)
transition_object_14 = smt.StateMachineTransition(state_object_after_transition_13, transition_function_14, state_object_after_transition_14)
state_object_after_transition_13.add_outgoing_transition(transition_object_14)
transition_object_15 = smt.StateMachineTransition(state_object_after_transition_14, transition_function_15, state_object_after_transition_15)
state_object_after_transition_14.add_outgoing_transition(transition_object_15)
transition_object_16 = smt.StateMachineTransition(state_object_after_transition_9, transition_function_16, state_object_after_transition_16)
state_object_after_transition_9.add_outgoing_transition(transition_object_16)
transition_object_17 = smt.StateMachineTransition(state_object_after_transition_16, transition_function_17, state_object_after_transition_17)
state_object_after_transition_16.add_outgoing_transition(transition_object_17)
transition_object_18 = smt.StateMachineTransition(state_object_after_transition_17, transition_function_18, state_object_after_transition_18)
state_object_after_transition_17.add_outgoing_transition(transition_object_18)
transition_object_19 = smt.StateMachineTransition(state_object_after_transition_18, transition_function_19, state_object_after_transition_19)
state_object_after_transition_18.add_outgoing_transition(transition_object_19)
transition_object_20 = smt.StateMachineTransition(state_object_after_transition_19, transition_function_20, state_object_after_transition_20)
state_object_after_transition_19.add_outgoing_transition(transition_object_20)
transition_object_21 = smt.StateMachineTransition(state_object_after_transition_20, transition_function_21, state_object_after_transition_21)
state_object_after_transition_20.add_outgoing_transition(transition_object_21)
transition_object_22 = smt.StateMachineTransition(state_object_after_transition_21, transition_function_22, state_object_after_transition_22)
state_object_after_transition_21.add_outgoing_transition(transition_object_22)

# write the state machine to a file

state_machine.write_to_file("generated-state-machine.gv")

# run it

state_machine.run()
