.PHONY: build-webapp-image
build-webapp-image:
	cd frontend && withproxy npm install && npm run dev-dist && cd ..
	docker build . -f docker_oss/Dockerfile -t feedback-tool
	echo "Finished building image!"

.PHONY: make-release
make-release:
	git diff-index --quiet HEAD -- || (echo "You have uncommited changes! Please commit them first" && exit 1)
	withproxy s2i build . registry.access.redhat.com/rhscl/python-36-rhel7 feedback-tool-app

.PHONY: build-dev-s2i-frontend-image
build-dev-s2i-frontend-image:
	git diff-index --quiet HEAD -- || (echo "You have uncommited changes! Please commit them first" && exit 1)
	withproxy s2i build . --context-dir=frontend/ registry.access.redhat.com/rhscl/nodejs-8-rhel7 feedback-tool-dev-frontend

.PHONY: build-s2i-webapp-image
build-s2i-webapp-image:
	git diff-index --quiet HEAD -- || (echo "You have uncommited changes! Please commit them first" && exit 1)
	withproxy s2i build . registry.access.redhat.com/rhscl/python-36-rhel7 feedback-tool-app


