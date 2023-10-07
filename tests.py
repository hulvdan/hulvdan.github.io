from build import process_region

value = process_region(
    "Test<NOT_IN_CV>SampleText<NOT_IN_CV_END>Test",
    opening="<NOT_IN_CV>",
    closing="<NOT_IN_CV_END>",
    remove=True,
)
error_message = f'"{value}" != "TestTest"'
assert value == "TestTest", error_message


value = process_region(
    "Test<NOT_IN_CV>SampleText<NOT_IN_CV_END>Test",
    opening="<NOT_IN_CV>",
    closing="<NOT_IN_CV_END>",
    remove=False,
)
error_message = f'"{value}" != "TestSampleTextTest"'
assert value == "TestSampleTextTest", error_message


value = process_region(
    "Test<NOT_IN_CV>SampleText<NOT_IN_CV_END>TestTest<NOT_IN_CV>SampleText<NOT_IN_CV_END>Test",
    opening="<NOT_IN_CV>",
    closing="<NOT_IN_CV_END>",
    remove=True,
)
error_message = f'"{value}" != "TestTestTestTest"'
assert value == "TestTestTestTest", error_message


value = process_region(
    "Test<NOT_IN_CV>SampleText<NOT_IN_CV_END>TestTest<NOT_IN_CV>SampleText<NOT_IN_CV_END>Test",
    opening="<NOT_IN_CV>",
    closing="<NOT_IN_CV_END>",
    remove=False,
)
error_message = f'"{value}" != "TestSampleTextTestTestSampleTextTest"'
assert value == "TestSampleTextTestTestSampleTextTest", error_message
