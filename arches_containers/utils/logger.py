import json
from yaspin import yaspin
from prettytable import PrettyTable

class AcOutputManager(object):
    """
    Coordinates and manages CLI messaging and using a yaspin spinner. It should be used as a context manager.

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
            cls.spinner = yaspin(text=cls.start_text)
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
    def write(message):
        '''
        Write a message to the spinner.
        '''
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
        AcOutputManager().spinner.text = message

    @staticmethod
    def complete_step(message):
        '''
        Write a completed message to the spinner (🟢).
        '''
        AcOutputManager().spinner.write(f"🟢 {message}")

    @staticmethod
    def skipped_step(message):
        '''
        Write a skipped message to the spinner (🟠).
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
        spinner_manager.spinner.write(f"🟢 {message}")
        spinner_manager.spinner.text = spinner_manager.start_text
        spinner_manager.spinner.ok("✅ 🏁 ")
        spinner_manager.stop_spinner()

    @staticmethod
    def fail(message):
        '''
        Write a failure message to the spinner and stop it. It will also exit the program with a status code of 1.
        '''
        spinner_manager = AcOutputManager()
        spinner_manager.spinner.write(f"🔴 {message}")
        spinner_manager.spinner.text = spinner_manager.start_text
        spinner_manager.spinner.fail("❌ ")
        spinner_manager.stop_spinner()
        exit(1)



