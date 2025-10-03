import json
from prettytable import PrettyTable

from rich.console import Console
from rich.spinner import Spinner as RichSpinner
from rich.live import Live
from rich.align import Align
from rich.text import Text
import arches_containers
from arches_containers import AC_VERSION as arches_containers_version

BANNER = f"""
_█████╗ ██████╗  ██████╗██╗  ██╗███████╗███████╗   ██████╗ ██████╗ ███╗   ██╗████████╗ █████╗ ██████╗███╗   ██╗███████╗██████╗ ███████╗
██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔════╝  ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗╚═██╔═╝████╗  ██║██╔════╝██╔══██╗██╔════╝
███████║██████╔╝██║     ███████║█████╗  ███████╗  ██║     ██║   ██║██╔██╗ ██║   ██║   ███████║  ██║  ██╔██╗ ██║█████╗  ██████╔╝███████╗
██╔══██║██╔══██╗██║     ██╔══██║██╔══╝  ╚════██║  ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██║  ██║  ██║╚██╗██║██╔══╝  ██╔══██╗╚════██║
██║  ██║██║  ██║╚██████╗██║  ██║███████╗███████║  ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║██████╗██║ ╚████║███████╗██║  ██║███████║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚══════╝v{arches_containers_version}
"""

MINIBANNER = f"""
_█████╗        ██████╗        ████████╗
██╔══██╗      ██╔════╝        ╚══██╔══╝
███████║      ██║                ██║   
██╔══██║      ██║                ██║  
██║  ██║      ╚██████╗           ██║  
╚═╝  ╚═╝rches  ╚═════╝ontainer   ╚═╝ools  v{arches_containers_version}
"""

def create_banner():
    """Display the ASCII art banner."""
    # Create gradient effect with different colors
    banner_lines = BANNER.strip().split('\n')
    minibanner_lines = MINIBANNER.strip().split('\n')
    colors = ["dark_red", "red3", "red1", "indian_red", "white", "bright_white"]
    
    styled_banner = Text()
    for i, line in enumerate(minibanner_lines):
        color = colors[i % len(colors)]
        if i == len(minibanner_lines) - 1:
            styled_banner.append(line, style=color)
        else:
            styled_banner.append(line + "\n", style=color)
    
    return styled_banner

class _RichSpinner:
    def __init__(self, text=""):
        self.console = Console()
        #self.console.rule(f"Arches Containers CLI v{arches_containers.AC_VERSION}")
        self.console.rule(style="bold red")
        self.console.print(Align.left(create_banner()))
        self.console.rule(style="bold red")
        self.text = text
        self._spinner = RichSpinner("dots", text=self.text)
        self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self, message=None):
        if message:
            self.text = message
            self._spinner.text = message
        if not self._live:
            self._live = Live(self._spinner, console=self.console, refresh_per_second=10, transient=True)
        else:
            self._live.update(self._spinner)
        
        self._live.start()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None

    def write(self, message, style=None):
        # Print immediately
        self.console.print(message, style=style)
        
    def ok(self, text=""):
        self.stop()
        if text:
            self.console.print(text)

    def fail(self, text=""):
        self.stop()
        if text:
            self.console.print(text)

    @property
    def text_attr(self):
        return self._spinner.text

    @text_attr.setter
    def text_attr(self, value):
        self._spinner.text = value

class AcOutputManager(object):
    """
    Coordinates and manages CLI messaging and using a (now rich-based) spinner. It should be used as a context manager.

    Example:
        with AcOutputManager("Starting...") as spinner: \n
            spinner.write("Doing something...") \n
            spinner.complete_step("Completed something.") \n
            spinner.text("Updating...") \n
            spinner.write("Doing something else...") \n
            spinner.success("Success") \n

    Methods:
        start_spinner(message: str): Starts the spinner with a message.
        stop_spinner(): Stops the spinner.
        write(message: str): Writes a message to the spinner.
        pretty_write_args(args: dict): Pretty-prints a dictionary in an ASCII table.
        text(message: str): Updates the spinner’s leading text.
        complete_step(message: str): Writes a completed step message (🟢).
        skipped_step(message: str): Writes a skipped step message (🟡).
        failed_step(message: str): Writes a failure message (🔴).
        success(message: str): Writes a success message, updates spinner text, sets OK status, then stops.
        fail(message: str): Writes a failure message, sets fail status, stops, and exits.
    """
    def __new__(cls, text=""):
        if not hasattr(cls, 'instance'):
            cls.instance = super(AcOutputManager, cls).__new__(cls)
            cls.start_text = text
            cls.spinner = _RichSpinner(text=cls.start_text)
        return cls.instance

    def __enter__(self):
        return self.spinner.__enter__()
    
    def __exit__(self, exc_type, exc_value, traceback):
        return self.spinner.__exit__(exc_type, exc_value, traceback)
    
    @staticmethod
    def start_spinner(message=""):
        if message:
            AcOutputManager().spinner.start(message)
        else:
            AcOutputManager().spinner.start()

    @staticmethod
    def stop_spinner():
        AcOutputManager().spinner.stop()

    @staticmethod
    def write(message, color=None):
        '''
        Write a message to the spinner, optionally specifying a color.
        '''
        if color:
            AcOutputManager().spinner.write(message, style=color)
        else:
            AcOutputManager().spinner.write(message)

    @staticmethod
    def pretty_write_args(args):
        '''
        Write a pretty-printed version of the args to the spinner in an ascii table.
        '''

        table = PrettyTable()
        table.align = "l"
        table.field_names = ["Argument", "Value"]
        for key, value in args.items():
            table.add_row([key, value])
        
        AcOutputManager.write(table.get_string())

    @staticmethod
    def text(message):
        '''
        Change the leading text in the spinner.
        '''
        AcOutputManager().spinner.text_attr = message

    @staticmethod
    def complete_step(message):
        '''
        Write a completed message to the spinner (🟢).
        '''
        AcOutputManager().spinner.write(f"🟢 {message}")

    @staticmethod
    def skipped_step(message):
        '''
        Write a skipped message to the spinner (🟡).
        '''
        AcOutputManager().spinner.write(f"🟡 {message}")

    @staticmethod
    def failed_step(message):
        '''
        Write a failure message to the spinner.
        '''
        AcOutputManager().spinner.write(f"🔴 {message}")

    @staticmethod
    def success(message):
        '''
        Write a success message to the spinner and stop it.
        '''
        spinner_manager = AcOutputManager()
        spinner_manager.write(f"🟢 {message}")
        spinner_manager.spinner.ok("🏁 Finished successfully")

    @staticmethod
    def fail(message):
        '''
        Write a failure message to the spinner and stop it. It will also exit the program with a status code of 1.
        '''
        spinner_manager = AcOutputManager()
        spinner_manager.write(f"🔴 {message}")
        spinner_manager.spinner.fail("❌ Finished with errors")
        exit(1)



