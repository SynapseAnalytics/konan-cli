from pydantic import BaseModel

def prediction_request(BaseModel):
    """Defines the schema of a prediction request
    Follow the convention of <field_name>: <type_hint>, ex:

    name: str
    age: int

    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info
    """
    # TODO: REQUIRED
    pass

def prediction_response(BaseModel):
    """Defines the schema of a prediction request
    Follow the convention of <field_name>: <type_hint>, ex:

    y: bool

    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info
    """
    # TODO: REQUIRED
    pass

def load_model():
    # TODO: REQUIRED
    # load your model and return it
    return model

def predict(prediction_request) -> prediction_response:
    # TODO: REQUIRED
    # write your prediction function, it takes the prediction request as input
    pass
