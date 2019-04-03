from locust import HttpLocust, TaskSet, task
from locust.exception import ResponseError
from jsonpath_rw import jsonpath, parse
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
import json


def checkResponse(actualResponse, expectedResponse):
	if str(actualResponse) not in str(expectedResponse):
		raise ResponseError("Response code " + str(actualResponse) + " does not match expected response code(s) " + str(expectedResponse))


def checkETagHeaderPresent(headers, expectedValue):
	if ETagHeaderPresent(headers) != expectedValue:
		if expectedValue:
			raise ResponseError("ETag header is missing from the response")
		else:
			raise ResponseError("ETag header found in response, while it was not expected")


def ETagHeaderPresent(headers):
	eTagHeader = [match.value for match in parse('$.ETag').find(headers)]
	return "W/" in str(eTagHeader)


def checkFormat(response, expectedFormat):
	print "expected format: " + expectedFormat
	actualFormat = format(response)
	if actualFormat != expectedFormat:
		raise ResponseError("Expected format of response body is " + str(expectedFormat) + ", but the following format was found: " + str(actualFormat))


def format(response):
	try:
		response.json()
		return "json"
	except ValueError:
		pass
	try:
		tree = ElementTree.fromstring(response.content)
		return "xml"
	except ParseError:
		pass
	return "unknown format"


def checkEmptyResponseBody(self, response, expectedValue):
	if emptyResponseBody(self, response) != expectedValue:
		if expectedValue:
			raise ResponseError("Non-empty response body")
		else:
			raise ResponseError("Empty response body")


def emptyResponseBody(self, response):
	return len(response.raw.read()) == 0


def checkTotalAboveZero(self, bundle, expectedValue):
	if totalAboveZero(self, bundle) != expectedValue:
		if expectedValue:
			raise ResponseError("Empty response body or empty search set")
		else:
			raise ResponseError("Non-empty response body or non-empty search set")


def totalAboveZero(self, bundle):
	total = [match.value for match in parse('$.total').find(bundle)]
	return (len(total) > 0 and total[0] > 0)


def checkTotalEquals(self, bundle, number, expectedValue):
	if totalEquals(self, bundle, number) != expectedValue:
		if expectedValue:
			raise ResponseError("Total number of resources does not match expected number of resources")
		else:
			raise ResponseError("Total number of resources matches unexpected value")


def totalEquals(self, bundle, number):
	# print bundle.json()
	total = [match.value for match in parse('$.total').find(bundle)]
	print "total: " + str(total)[1:-1] + " expected: " + str(number)
	return (len(total) > 0 and total[0] == number)


def checkResourceTypePresent(self, bundle, type, expectedValue):
	if resourceTypePresent(self, bundle, type) != expectedValue:
		if expectedValue:
			raise ResponseError("Resource of type: " + type + " not found in response body, while it was expected")
		else:
			raise ResponseError("Resource of type: " + type + " found in response body, while it was not expected")


def resourceTypePresent(self, body, type):
	resourceType = [match.value for match in parse('$.resourceType').find(body)]
	typePresent = type in resourceType
	if "Bundle" in resourceType:
		resourceType = [match.value for match in parse('$.entry[*].resource.resourceType').find(body)]
		# print str(resourceType)[1:-1]
		typePresent = typePresent or type in resourceType
	return typePresent


def checkElementsPresent(self, resource, elements, expectedValue):
	if elementsPresent(self, resource, elements) != expectedValue:
		if expectedValue:
			raise ResponseError("Not all listed elements ("+', '.join(elements)+") are present in response body")
		else:
			raise ResponseError("All listed elements ("+', '.join(elements)+") are present in response body")


def checkResourceIDpresent(self, bundle, id, expectedValue):
	if resourceIDpresent(self, bundle, id) != expectedValue:
		if expectedValue:
			raise ResponseError("Expected to find resource with id=" + id + ", but it was not found")
		else:
			raise ResponseError("Resource with id=" + id + " was found, but it was not expected")


def resourceIDpresent(self, bundle, id):
	ids = [match.value for match in parse('$.entry[*].resource.id').find(bundle)]
	return id in ids


def elementsPresent(self, resource, elements):
    for element in elements:
        if element not in resource.keys():
            return False
    return True


def checkNoOtherElementsPresent(self, resource, elements, expectedValue):
	if noOtherElementsPresent(self, resource, elements) != expectedValue:
		if expectedValue:
			raise ResponseError("Other elements than listed elements ("+', '.join(elements)+") are present in response body")
		else:
			raise ResponseError("No other elements than listed elements ("+', '.join(elements)+") are present in response body")


def noOtherElementsPresent(self, resource, elements):
	return len(resource) == (len(elements) + 3)  # check if no other elements beside resourceType, id, meta, listed elements


def checkOperationOutcomeIssueCode(self, OO, code, expectedValue):
	if operationOutcomeIssueCode(self, OO, code) != expectedValue:
		if expectedValue:
			raise ResponseError("Expected code: " + code + " not found")
		else:
			raise ResponseError("Code: " + code + " found, which was not expected")


def operationOutcomeIssueCode(self, OO, code):
	codes = [match.value for match in parse('$.issue[*].code').find(OO)]
	return code in codes


def checkTagPresent(self, resource, tag, expectedValue):
	if tagPresent(self, resource, tag) != expectedValue:
		if expectedValue:
			raise ResponseError(tag + " tag is missing from response body")
		else:
			raise ResponseError(tag + " tag was found in response body")


def tagPresent(self, resource, tag):
	tags = [match.value for match in parse('$.meta.tag[*].code').find(resource)]
	return tag in tags


def checkBatchSucces(self, inputBody, responseBody, expectedValue):
	if batchSucces(self, inputBody, responseBody) != expectedValue:
		if expectedValue:
			raise ResponseError("Not all entries in the batch succeeded")
		else:
			raise ResponseError("All entries in the batch succeeded, while this was not expected")


def batchSucces(self, inputBody, responseBody):
	request = [match.value for match in parse('$.entry[*].request.method').find(inputBody)]
	response = [match.value for match in parse('$.entry[*].response.status').find(responseBody)]
	for i in range(0, len(request)):
		if (request[i] == "DELETE" and response[i] != "204") or (request[i] != "DELETE" and response[i] not in ["200", "201"]):
			return False
	return True
