from python_utils import GlobalTimer, TimerManager, get_global_timer_manager
import time

manager = get_global_timer_manager()
for i in range(10):
    with manager("function1"):
        time.sleep(0.1)
        # do something
        pass
    with manager("function2"):
        # do something else
        time.sleep(0.2)
        pass

# for _ in range(200):
#     with GlobalTimer("testing"):
#         a = 2
#         b = 3
#         c = a + b
#         time.sleep(0.01)