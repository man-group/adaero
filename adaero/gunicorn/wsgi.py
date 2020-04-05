from paste.deploy import loadapp

application = loadapp("config:/opt/app-root/src/adaero/example.ini")
