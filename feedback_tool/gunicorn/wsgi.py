from paste.deploy import loadapp

application = loadapp("config:feedback_tool/example.ini", relative_to=".")
