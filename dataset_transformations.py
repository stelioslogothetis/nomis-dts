from type_hints import *
from pyjstat import pyjstat  # type: ignore
from logging import getLogger

logger = getLogger("DTS-Logger")


class DatasetTransformations:
    """
    Class containing methods for transforming the data retrieved from Cantabular such that it is ready for transmission
    to the Nomis system.

    :param table: A pyjstat dataframe containing the data to be used/transformed.
    :ivar table: Initial value: table.
    :vartype table: Dataset
    """

    def __init__(self, table: pyjstat.Dataset,
                 geography_flag: bool = False,
                 table_geography: Union[pyjstat.Dataset, None] = None) -> None:
        self.table = table
        self.geography_flag = geography_flag
        self.table_geography = table_geography
        self.validate_table()

    def validate_table(self):
        """
        Method for validating the table, ensuring it is of the correct type and contains sufficient keys.

        :raises TypeError: If the dataset is not of the correct type, i.e., a pyjstat Dataset.
        :raises LookupError: If the table is devoid of a "dimension" key, which is required for the transformations.
        """
        if not isinstance(self.table, pyjstat.Dataset):
            raise TypeError(f"Table was detected as type {type(self.table)}. "
                            f"This is invalid, the table must be a pyjstat.Dataset.")
        if "dimension" not in self.table:
            raise KeyError("Table supplied contains no dimensions key.")
        logger.debug("Table validated successfully.")

    @staticmethod
    def dataset_creation(dataset_id: str, dataset_title: str) -> NomisDataset:
        """
        Method for initialising a Nomis-style dataset using an inputted ID and title.

        :param dataset_id: A valid string representing the ID of the dataset to be created.
        :param dataset_title: A valid string representing the title of the dataset to be created.

        :raises TypeError: If `dataset_id` or `dataset_title` are not valid strings (str types).
        :raises ValueError: If `dataset_id` or `dataset_title` have a length of 0 (i.e., are empty).

        :return: If no exception is raised, an initialised dataset as a Python dict with valid keys and values.
        """
        if not isinstance(dataset_id, str):
            raise TypeError(f"The dataset id (inputted: {dataset_id}) must be a string.")
        if not isinstance(dataset_title, str):
            raise TypeError(f"The dataset title (inputted: {dataset_title}) must be a string.")
        if len(dataset_id) == 0:
            raise ValueError(f"The dataset id must not be empty.")
        if len(dataset_title) == 0:
            raise ValueError(f"The dataset title must not be empty.")

        ds = {
            "id": dataset_id,
            "title": dataset_title,
            "contactId": "Census",
            "isAdditive": True,
            "isFlagged": False,
            "derivedFrom": None,
            "restrictedAccess": False,
            "minimumRound": 0,
            "online": True
        }
        logger.debug("Initialised the dataset in the Nomis format.")
        return ds

    def variable_creation(self) -> List[Variables]:
        """
        Method for converting the variable data from the pyjstat dataframe into valid variables for communication
        with the Nomis API.

        :return: A list of variables.
        """
        requests = [
            {
                "name": dimension,
                "label": self.table["dimension"][dimension]["label"],
                "defaults": None
            }
            for dimension in self.table["dimension"]
        ]
        logger.debug("Prepared the variable requests.")
        return requests

    def type_creation(self) -> List[Variables]:
        """
        Method for creating a valid variable type using the pyjstat dataframe for communication
        with the Nomis API

        :raises KeyError: If the dataframe doesn't contain any dimension information
        :return: A list of types (should usually be a single dictionary inside of a list)
        """
        requests = []
        for dimension in self.table["dimension"]:
            requests.append(
                {
                    "id": "1000000",
                    "reference": dimension,
                    "title": self.table["dimension"][dimension]["label"],
                    "titlePlural": self.table["dimension"][dimension]["label"],
                }
            )
        logger.debug("Prepared types requests.")
        return requests

    def category_creation(self, type_ids: List[str]) -> List[Variables]:
        """
        Method for constructing a list of variable categories, using the jsonstat table retrieved from cantabular.

        :return: A list of variable categories.
        """

        if not isinstance(type_ids, list):
            raise TypeError("Invalid type_ids param, must be a list.")

        requests = []
        counter = 0
        for dimension in self.table["dimension"]:
            for label in self.table["dimension"][dimension]["category"]["label"]:
                requests.append(
                    {
                        "code": label,
                        "title": self.table["dimension"][dimension]["category"]["label"][label],
                        "ancestors": None,
                        "typeId": type_ids[counter],
                        "validity": {
                            "select": True,
                            "make": False
                        }
                    }
                )
            counter += 1
        logger.debug("Prepared category requests.")
        return requests

    def assign_dimensions(self, key: Union[str, None]) -> List[Dimensions]:
        """
        Method for using the jsonstat table to construct a list of dimensions, based on the initial query to
        cantabular.

        :param key: The key in the pyjstat dataframe corresponding with the dimensions/variables to be appended to the
            dataset.

        :return: A list of dataset dimensions.
        """

        requests = []
        index = 0
        if self.geography_flag is True:
            requests.append(
                {
                    "name": "geography",
                    "label": "geography",
                    "isAdditive": True,
                    "variable": {
                        "name": "geography",
                        "view": None
                    },
                    "role": "Spatial",
                    "canFilter": True,
                    "defaults": None,
                    "database": {
                        "isKey": True,
                        "index": index,
                        "defaultView": None,
                        "discontinuities": None
                    },
                }
            )
            index += 1

        for dimension in self.table["dimension"]:
            if dimension == key:
                is_key = True
            else:
                is_key = False
            requests.append(
                {
                    "name": dimension,
                    "label": self.table["dimension"][dimension]["label"],
                    "isAdditive": True,
                    "variable": {
                        "name": dimension,
                        "view": None
                    },
                    "role": "Normal",
                    "canFilter": True,
                    "defaults": None,
                    "database": {
                        "isKey": is_key,
                        "index": index,
                        "defaultView": None,
                        "discontinuities": None
                    },
                }
            )
            index += 1

        logger.debug("Prepared dimensions requests.")
        return requests

    def observations(self, dataset_id: str) -> Observations:
        """
        Method for creating dataset observations.

        :param dataset_id: A valid dataset ID, which must be a nonempty string.

        :raises TypeError: If the `dataset_id` is not a string.
        :raises ValueError: If the `dataset_id` is an empty string.

        :return: A python dict representing dataset dimensions.
        """
        if not isinstance(dataset_id, str):
            raise TypeError(f"The dataset id (inputted: {dataset_id}) must be a string.")
        if len(dataset_id) == 0:
            raise ValueError(f"The dataset id must not be empty.")

        if self.table_geography is None:
            data = self.table
        else:
            data = self.table_geography

        dimensions = []
        codes = []

        counter = 0
        for dimension in data["dimension"]:
            if counter == 0:
                dimensions.append("geography")
                codes.append(data["dimension"][dimension]["category"]["index"])
                counter += 1
                continue

            dimensions.append(dimension)
            codes.append(data["dimension"][dimension]["category"]["index"])

        logger.debug("Prepared observations.")
        return (
            {
                "dataset": dataset_id,
                "dimensions": dimensions,
                "codes": codes,
                "values": data["value"],
                "statuses": None
            }
        )

    @staticmethod
    def variable_metadata_request(uuids_metadata: List[UuidMetadata]) -> list:
        """
        Method for the construction of metadata in a format ready to be transmitted to Nomis.

        :param uuids_metadata: A list of namedtuples, each containing a UUID and some metadata associated with that UUID.

        :raises TypeError: If the uuids_metadata passed is not a list, or any of the elements contained in uuids_metadata
            is not a valid instance of the UuidMetadata namedtuple.

        :return: A list of metadata, ready to be sent to the Nomis system.
        """
        if not isinstance(uuids_metadata, list):
            raise TypeError("Parameter must be in a list.")
        for elem in uuids_metadata:
            if not isinstance(elem, UuidMetadata):
                raise TypeError("Parameter contains invalid types.")
        requests = [
            {
                "id": None,
                "belongsTo": id_md.uuid,
                "description": None,
                "created": None,
                "validFrom": None,
                "validTo": None,
                "include": None,
                "meta": [
                    {
                        "role": "note",
                        "properties": [
                            {
                                "prefix": "dc",
                                "property": "description",
                                "value": id_md.metadata["description"]
                            }
                        ]
                    }
                ]
            }
            for id_md in uuids_metadata]
        logger.debug("Prepared metadata.")
        return requests
