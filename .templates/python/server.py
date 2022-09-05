from konan_sdk.konan_service.services import KonanService
from konan_sdk.konan_service.models import KonanServiceBaseModel
from konan_sdk.konan_service.serializers import (
    KonanServiceBasePredictionRequest, KonanServiceBasePredictionResponse,
    KonanServiceBaseEvaluateRequest, KonanServiceBaseEvaluateResponse,
    )

from pydantic import BaseModel, validator
from typing import Optional

# TODO: alter parent
from konan_model.predict import prediction_request, prediction_response, predict


class MyPredictionRequest(prediction_request):
    """Defines the schema of a prediction request

    Follow the convention of <field_name>: <type_hint>
    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info

    Optionally add validators for your features
    Follow the pydantic convention
    Check https://pydantic-docs.helpmanual.io/usage/validators/ for more info
    """
    pass

class MyPredictionResponse(prediction_response):
    """Defines the schema of a prediction response

    Follow the convention of <field_name>: <type_hint>
    Check https://pydantic-docs.helpmanual.io/usage/models/ for more info

    Optionally add validators for your features
    Follow the pydantic convention
    Check https://pydantic-docs.helpmanual.io/usage/validators/ for more info
    """
    pass


class MyModel(KonanServiceBaseModel):
    def __init__(self):
        """Add logic to initialize your actual model here

        Maybe load weights, connect to a database, etc ..
        For example, the following code will load a model saved as a model.pickle file in the models/ directory
        import pickle
        from konan_sdk.konan_service import constants as Konan_Constants
        self.loaded_model = pickle.load(open(f"{Konan_Constants.MODELS_DIR}/model.pickle", 'rb'))
        """
        super().__init__()
        print("reading artifacts from /app/artifacts")
        f = open(f'/app/artifacts/weights.txt', "r")
        print(f.read())

    def predict(self, req: MyPredictionRequest) -> MyPredictionResponse:
        """Makes an intelligent prediction

        Args:
            req (MyPredictionRequest): raw request from API

        Returns:
            MyPredictionResponse: this will be the response returned by the API
        """
        pass

    def evaluate(self, req: KonanServiceBaseEvaluateRequest) -> KonanServiceBaseEvaluateResponse:
        """Evaluates the model based on passed predictions and their ground truths

        Args:
            req (KonanServiceBaseEvaluateRequest): includes passed predictions and their ground truths

        Returns:
            KonanServiceEvaluateResponse: the evaluation(s) of the model based on some metrics
        """
        # TODO: [5] Implement your evaluation logic
        evaluation = "" # Use your logic to make an evaluation
        return evaluation


app = KonanService(MyPredictionRequest, MyPredictionResponse, MyModel)
