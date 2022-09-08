from pydantic import BaseModel


class prediction_request(BaseModel):
    """Defines the schema of a prediction request
    Follow the convention of <field_name>: <type_hint>, ex:

    name: str
    age: int

    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info
    """
    # TODO: REQUIRED
    pass


class prediction_response(BaseModel):
    """Defines the schema of a prediction request
    Follow the convention of <field_name>: <type_hint>, ex:

    y: bool

    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info
    """
    # TODO: REQUIRED
    pass


class Model:
    def __init__(self, artifacts_base_path):
        """Initialize your model and artifacts here

        Args:
            artifacts_path (string): base path of artifacts folder path
        """
        # TODO: load your model and encoders (if exists) here
        # Ex:
        # self.model = pickle.load(open(f"{artifacts_base_path}/model.pickle", 'rb'))
        # self.encoders = pickle.load(open(f"{artifacts_base_path}/encoders/OneHotEncoder.pickle", 'rb'))

    def predict(self, prediction_request) -> prediction_response:
        # TODO: REQUIRED
        # write your prediction function, it takes the prediction request as input
        # Ex:
        # prediction = self.model.predict(prediction_request)

        # return prediction
        pass
