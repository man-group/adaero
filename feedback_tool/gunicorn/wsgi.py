from paste.deploy import loadapp

application = loadapp("config:/opt/app-root/src/feedback_tool/example.ini")
