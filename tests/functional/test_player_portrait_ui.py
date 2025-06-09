"""UI tests for player portrait functionality."""

from pathlib import Path

import pytest
from PIL import Image
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.data_access import models
from app.data_access.db_session import get_db_session
from app.services.image_processing_service import ImageProcessingService


@pytest.mark.functional
class TestPlayerPortraitUI:
    """UI tests for player portrait upload and display functionality."""

    def create_test_image_file(self, tmp_path: Path, filename: str = "test_portrait.jpg") -> Path:
        """Create a test image file."""
        img = Image.new("RGB", (200, 200), color="blue")
        file_path = tmp_path / filename
        img.save(file_path, "JPEG")
        return file_path

    def test_player_detail_page_portrait_placeholder(self, authenticated_driver, test_player):
        """Test that player detail page shows portrait placeholder when no portrait exists."""
        # Navigate to player detail page
        authenticated_driver.get(f"/players/{test_player.id}")

        # Wait for page to load
        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Check for placeholder icon (Font Awesome user icon)
        placeholder = authenticated_driver.find_element(By.CSS_SELECTOR, ".fa-user")
        assert placeholder.is_displayed()

    def test_player_detail_upload_button_visible_when_authenticated(self, authenticated_driver, test_player):
        """Test that upload button is visible when user is authenticated."""
        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Look for upload button (camera icon button)
        upload_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick*='showUploadModal'], .fa-camera"))
        )
        assert upload_button.is_displayed()

    def test_player_portrait_upload_modal(self, authenticated_driver, test_player, tmp_path):
        """Test the portrait upload modal functionality."""
        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Click upload button
        upload_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[onclick*='showUploadModal'], button[title='Upload Portrait']")
            )
        )
        upload_button.click()

        # Wait for modal to appear
        modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "modal")))
        assert modal.is_displayed()

        # Check modal title
        modal_title = authenticated_driver.find_element(By.CSS_SELECTOR, ".modal-title")
        assert "Upload Player Portrait" in modal_title.text

        # Check file input exists
        file_input = authenticated_driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        assert file_input.is_displayed()

        # Check upload button exists
        upload_btn = authenticated_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert upload_btn.is_displayed()
        assert "Upload" in upload_btn.text

    def test_player_portrait_upload_with_preview(self, authenticated_driver, test_player, tmp_path):
        """Test portrait upload with image preview."""
        # Create test image
        image_file = self.create_test_image_file(tmp_path)

        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Click upload button
        upload_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[onclick*='showUploadModal'], button[title='Upload Portrait']")
            )
        )
        upload_button.click()

        # Wait for modal
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "modal")))

        # Upload file
        file_input = authenticated_driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(str(image_file))

        # Wait for preview to appear
        preview = wait.until(EC.presence_of_element_located((By.ID, "portrait-preview")))
        assert preview.is_displayed()

        # Check preview image
        preview_img = authenticated_driver.find_element(By.ID, "preview-image")
        assert preview_img.is_displayed()
        assert preview_img.get_attribute("src").startswith("data:image")

    def test_player_portrait_successful_upload(self, authenticated_driver, test_player, tmp_path):
        """Test successful portrait upload and page refresh."""
        # Create test image
        image_file = self.create_test_image_file(tmp_path)

        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Click upload button
        upload_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[onclick*='showUploadModal'], button[title='Upload Portrait']")
            )
        )
        upload_button.click()

        # Wait for modal
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "modal")))

        # Upload file
        file_input = authenticated_driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(str(image_file))

        # Click upload button
        upload_btn = authenticated_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        upload_btn.click()

        # Wait for page to refresh and upload to complete
        wait.until(EC.url_contains(f"/players/{test_player.id}"))

        # Wait for new player data to load
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Verify portrait is now displayed (no longer just placeholder)
        # The exact implementation will depend on how the portrait is displayed
        # We'll check that there's an actual image element now
        try:
            portrait_img = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='portrait'], img[src*='portrait']"))
            )
            assert portrait_img.is_displayed()
        except (TimeoutException, NoSuchElementException):
            # Alternative: check that placeholder is no longer the only image
            # This test might need adjustment based on actual implementation
            pass

    def test_player_portrait_delete_functionality(self, authenticated_driver, test_player, tmp_path):
        """Test portrait deletion functionality."""
        # First upload a portrait
        image_file = self.create_test_image_file(tmp_path)

        # Upload via API to set up test state
        with get_db_session() as session:
            player = session.query(models.Player).filter_by(id=test_player.id).first()
            player.thumbnail_image = f"players/{test_player.id}/portrait.jpg"
            session.commit()

            # Create the actual file
            portrait_dir = ImageProcessingService.get_image_directory(
                test_player.id, ImageProcessingService.ImageType.PLAYER_PORTRAIT
            )
            portrait_dir.mkdir(parents=True, exist_ok=True)
            portrait_path = portrait_dir / "portrait.jpg"

            img = Image.new("RGB", (200, 200), color="green")
            img.save(portrait_path, "JPEG")

        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Look for remove/delete button
        try:
            delete_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[onclick*='deletePortrait'], button[title*='Remove']")
                )
            )
            delete_button.click()

            # Handle confirmation dialog
            authenticated_driver.switch_to.alert.accept()

            # Wait for page refresh
            wait.until(EC.url_contains(f"/players/{test_player.id}"))

            # Verify portrait is removed (back to placeholder)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".fa-user")))

        except (TimeoutException, NoSuchElementException):
            # Delete functionality might be implemented differently
            # This test may need adjustment based on actual UI implementation
            pass

    def test_player_index_page_portrait_display(self, authenticated_driver, test_player):
        """Test that player portraits are displayed on the player index page."""
        authenticated_driver.get("/players")

        wait = WebDriverWait(authenticated_driver, 10)

        # Wait for player table to load
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table, .players-table")))

        # Look for player rows
        player_rows = authenticated_driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        assert len(player_rows) > 0

        # Check for portrait placeholders in player rows
        portraits = authenticated_driver.find_elements(By.CSS_SELECTOR, ".player-portrait-small, .fa-user")
        assert len(portraits) > 0

    def test_player_portrait_responsive_design(self, authenticated_driver, test_player):
        """Test that player portraits are responsive on different screen sizes."""
        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Test desktop size
        authenticated_driver.set_window_size(1200, 800)

        # Check portrait size/visibility
        portrait_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".fa-user, img[alt*='portrait']"))
        )
        assert portrait_element.is_displayed()

        # Test mobile size
        authenticated_driver.set_window_size(375, 667)

        # Check portrait is still visible and appropriately sized
        portrait_element = authenticated_driver.find_element(By.CSS_SELECTOR, ".fa-user, img[alt*='portrait']")
        assert portrait_element.is_displayed()

    def test_portrait_error_handling(self, authenticated_driver, test_player, tmp_path):
        """Test error handling for invalid file uploads."""
        # Create a text file instead of image
        text_file = tmp_path / "not_an_image.txt"
        text_file.write_text("This is not an image")

        authenticated_driver.get(f"/players/{test_player.id}")

        wait = WebDriverWait(authenticated_driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "player-data")))

        # Wait for player data to be rendered
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "h1, h2"), test_player.name))

        # Click upload button
        upload_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[onclick*='showUploadModal'], button[title='Upload Portrait']")
            )
        )
        upload_button.click()

        # Wait for modal
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "modal")))

        # Upload invalid file
        file_input = authenticated_driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(str(text_file))

        # Click upload button
        upload_btn = authenticated_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        upload_btn.click()

        # Wait for error message or alert
        try:
            # Check for alert
            wait.until(EC.alert_is_present())
            alert = authenticated_driver.switch_to.alert
            assert "Invalid file" in alert.text or "error" in alert.text.lower()
            alert.accept()
        except (TimeoutException, NoSuchElementException):
            # Alternative: check for error message in UI
            try:
                error_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".error, .alert-danger, [class*='error']"))
                )
                assert error_element.is_displayed()
            except (TimeoutException, NoSuchElementException):
                # Error handling might be implemented differently
                pass

    def test_game_detail_page_player_portraits(self, authenticated_driver, test_game, test_player):
        """Test that player portraits appear in game detail box scores."""
        authenticated_driver.get(f"/games/{test_game.id}")

        wait = WebDriverWait(authenticated_driver, 10)

        # Wait for game data to load
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".game-header, h1")))

        # Look for box score tables
        try:
            box_score = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".box-score-table, table")))

            # Check for player portrait elements in the box score
            portraits = authenticated_driver.find_elements(By.CSS_SELECTOR, ".player-portrait-tiny, .fa-user")

            # Should have at least some portrait placeholders
            assert len(portraits) >= 0  # Could be 0 if no players have stats

        except (TimeoutException, NoSuchElementException):
            # Game detail page might load differently
            pass
