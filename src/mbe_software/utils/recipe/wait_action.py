import logging

# Local imports
from .recipe_action import RecipeAction

logger = logging.getLogger(__name__)

# Base class for actions that may have to pause, resume, and stop
# i.e. recipe action is not executed instantaneously
class WaitAction(RecipeAction):
    def __init__(self):
        super().__init__()
        
    def pause(self):
        raise NotImplementedError("This method should be implemented!")
    
    def resume(self):
        raise NotImplementedError("This method should be implemented!")
    
    def stop(self):
        raise NotImplementedError("This method should be implemented!")