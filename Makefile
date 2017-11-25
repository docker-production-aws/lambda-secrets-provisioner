FUNCTION_NAME ?= secretsProvisioner
S3_BUCKET ?= 543279062384-cfn-lambda
S3_OBJECT_VERSION ?= $$(aws s3api list-object-versions --bucket $(S3_BUCKET) --prefix $(FUNCTION_NAME).zip \
--query 'Versions[?IsLatest].VersionId' --output text)

build: clean
	@ echo "Building $(FUNCTION_NAME).zip..."
	@ cd src && pip install -t vendor/ -r requirements.txt --upgrade
	@ mkdir -p build
	@ cd src && zip -9 -r ../build/$(FUNCTION_NAME).zip * -x *.pyc -x requirements_test.txt -x tests/ -x tests/**\*
	@ echo "Built build/$(FUNCTION_NAME).zip"

publish:
	@ echo "Publishing $(FUNCTION_NAME).zip to s3://$(S3_BUCKET)..."
	@ aws s3 cp --quiet build/$(FUNCTION_NAME).zip s3://$(S3_BUCKET)
	@ echo "Published to S3 URL: https://s3.amazonaws.com/$(S3_BUCKET)/$(FUNCTION_NAME).zip"
	@ echo "S3 Object Version: $(S3_OBJECT_VERSION)"

clean:
	@ rm -rf src/*.pyc src/vendor build
	@ echo "Removed all distributions"