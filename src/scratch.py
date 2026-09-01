

class TestClass():
    def __init__(self):
        print("enabled!")
        self.enabled = True

    def only_if_enabled(method):
            def wrapper(*args, **kwargs):
                # Decorator itercepts the method arguments, including the first argument
                # which is the instance (in place of "self")
                if not args[0].enabled:
                    print("Won't run, I am disabled!")
                    # logger.warning(f"Motor {motor.name} is currently disabled.")
                    return
                return method(*args, **kwargs)
            return wrapper

    def disable(self):
         print("disabled!")
         self.enabled = False

    @only_if_enabled
    def run(self):
        print("I ran!")

if __name__ == "__main__":
    test = TestClass()
    test.run()
    test.disable()
    test.run()