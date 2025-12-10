# Creating A Recipe Action

## Basic Instructions

1. Create a new file, name it something descriptive (follow pattern of existing files)

2. Import logging and either the **RecipeAction** class or **WaitAction** class to extend with your new action class, and set the logger (boilerplate below).

3. Implement the methods of whichever class you chose to extend (check their files to see which methods raise NotImplementedError by default)

4. Add an import for your class to the **__init__.py** package file, this will make it available in the main file through recipe.MyRecipeAction (Your class name instead of MyRecipeAction)

5. Add an instance of your class to the **recipe_action_map** in the main program (follow the pattern there, use Ctrl+F to find it if needed).

## New Action Boilerplate

```
import logging
from .recipe_action import RecipeAction

logger = logging.getLogger(__name__)

class MyRecipeAction(RecipeAction):
    def __init__(self):
        super().__init__()
```

## Action Class Requirements
- You **MUST** emit the can_continue signal by calling `self.can_continue()` at the end of your run() method or when some other condition is met, this lets the recipe runner in the main program know the step is complete and it can continue with the recipe.

- Make sure your class *resets its state* when run is called (any attributes that aren't constant between steps or recipes should be set to their default values). See wait_until_setpoint.py for an example of this.