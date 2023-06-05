import os
import logging
from dependency import core_func

PROJECT_ROOT = os.path.dirname(__file__)
KV_FILE_PATH = os.path.join(PROJECT_ROOT, "dependency", "kv_lang.kv")
INPUT_FOLDER_PATH = os.path.join(PROJECT_ROOT, "input")
OUTPUT_FOLDER_PATH = os.path.join(PROJECT_ROOT, "output")
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "log", "log.txt")

logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO, format="%(asctime)s :: %(levelname)s :: %(message)s")
logging.info(f"########################### START APPLICATION ###########################")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.uix.popup import Popup


class RunPop(Popup):
    """
    Template for the run button pop up window
    :method update_popuptext" to update the pop up label
    """
    def update_popuptext(self, text):
        self.ids.runpop_label.text = text

class UpdatePop(Popup):
    """
    Template for the update button pop up window
    :method update_popuptext" to update the pop up label
    """
    def update_popuptext(self, text):
        self.ids.updatepop_label.text = text

class MainWindow(Screen):
    """
    Main menu for the program
    :method run_btn: control the run button pop up message
    :method run_output: trigger the main function
    """

    def run_btn(self):
        popup = RunPop()
        if self.run_output():
            popup.update_popuptext("Run successfully")
            self.ids.source_filename.text = ""
            self.ids.tablelist_filename.text = ""
        else:
            popup.update_popuptext("Run failed")
        popup.open()

    def run_output(self):
        try:
            source_filename = self.ids.source_filename.text
            tablelist_filename = self.ids.tablelist_filename.text

            source_file_path = os.path.join(INPUT_FOLDER_PATH, source_filename)
            table_list_path = os.path.join(INPUT_FOLDER_PATH, tablelist_filename)

            config = App.get_running_app().CONFIG

            if not os.path.exists(source_file_path) or not source_file_path.endswith(".csv"):
                raise UserWarning(f"The source file not exists, '{source_file_path}'")
            
            if not os.path.exists(table_list_path) or not table_list_path.endswith("txt"):
                raise UserWarning(f"The table list file not exists, '{table_list_path}'")
            
            if config is None:
                raise UserWarning("The config parameters has not been provided")

            core_func.main(source_file_path, OUTPUT_FOLDER_PATH, table_list_path, config)

            return True
        
        except Exception as e:
            logging.error(e)
            return False

class TutorialWindow(Screen):
    """
    Tutorial window
    """
    pass

class ParameterWindow(Screen):
    """
    Parameter window to update the parameter values
    :method update_btn: control the update button pop up message
    :method update_output: to update the parameters value and display the latest parameters
    """

    def update_btn(self):
        popup = UpdatePop()
        if self.update_output():
            popup.update_popuptext("Update successfully")
        else:
            popup.update_popuptext("Update failed")
        popup.open()

    def update_output(self):
        try:
            config_filename = self.manager.get_screen("main").ids.config_filename.text
            parameter_config_path = os.path.join(INPUT_FOLDER_PATH, config_filename)

            if not os.path.exists(parameter_config_path):
                raise UserWarning(f"The config file not exists, '{parameter_config_path}'")
            
            config = core_func.get_parameter_config(parameter_config_path)
            App.get_running_app().CONFIG = config

            display_label = ""
            for header, env_items in config.items():
                display_label += f"[{header}]"
                display_label += "\n"
                for key, value in env_items.items():
                    display_label += key
                    display_label += ": "
                    display_label += value
                    display_label += "\n"

                display_label += "\n"

            self.ids.config_label.text = display_label
            logging.info(f"Updated the config parameters, '{parameter_config_path}'")
            return True
        
        except Exception as e:
            logging.error(e)
            return False

class WindowManager(ScreenManager):
    """
    Window manager
    """
    pass

# to load the kv languange file
kv = Builder.load_file(KV_FILE_PATH)

class sqlwarehouse_ddl_generatorApp(App):
    """
    Application main
    :method build:
    """
    CONFIG = None

    def build(self):
        return kv

if __name__ == "__main__":
    sqlwarehouse_ddl_generatorApp().run()
