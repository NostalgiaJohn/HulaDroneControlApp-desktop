import pyhula

instance = pyhula.UserApi()
instance.connect()

while True:
    # 输出角度信息
    print(instance.get_yaw())
