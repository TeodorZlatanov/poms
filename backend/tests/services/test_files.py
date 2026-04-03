from services.files import detect_file_type, extract_text_from_csv


class TestDetectFileType:
    def test_csv_by_content_type(self):
        result = detect_file_type("data.csv", "text/csv", b"col1,col2\nval1,val2")
        assert result == "csv"

    def test_csv_by_extension(self):
        result = detect_file_type("data.csv", "application/octet-stream", b"col1,col2\nval1,val2")
        assert result == "csv"

    def test_image_by_content_type(self):
        result = detect_file_type("scan.png", "image/png", b"\x89PNG")
        assert result == "image"

    def test_image_by_extension(self):
        result = detect_file_type("scan.jpg", "application/octet-stream", b"\xff\xd8\xff")
        assert result == "image"


class TestExtractTextFromCsv:
    async def test_basic_csv(self):
        csv_data = b"Item,Quantity,Price\nWidget,10,12.50\nGadget,5,25.00"
        result = await extract_text_from_csv(csv_data)
        assert "Widget" in result
        assert "12.5" in result
        assert "Gadget" in result

    async def test_single_column_csv(self):
        csv_data = b"Name\nAlice\nBob"
        result = await extract_text_from_csv(csv_data)
        assert "Alice" in result
        assert "Bob" in result
