import pyhula

instance = pyhula.UserApi()
instance.connect()

# 输出电池信息
print(instance.get_battery())
