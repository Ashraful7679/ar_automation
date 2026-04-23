from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path):
        """
        Parses the file and returns a list of dictionaries or rows representing the raw data.
        Should also set self.headers.
        """
        pass

    @abstractmethod
    def transform(self, raw_data):
        """
        Transforms raw data into the final desired output format (Sl No, Inv No, etc.)
        Returns (headers, rows)
        """
        pass
