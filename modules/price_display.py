"""
Price Display Module for LED Wall Client
Generates visual representation of prices for LED wall display
"""
import os
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger("led_client.price_display")

class PriceDisplay:
    """Handles generation of price display images for LED wall"""

    def __init__(self, width=256, height=320):
        """Initialize price display generator

        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height

        # LED wall optimized colors (high contrast)
        self.colors = {
            'background': (0, 0, 0),      # Black background
            'text': (255, 255, 255),      # White text
            'border': (255, 255, 255),    # White borders
            'shadow': (64, 64, 64)        # Dark gray shadow
        }

        # Calculate layout dimensions
        self.rows = 5
        self.row_height = height // self.rows
        self.half_width = width // 2

        # Try to load a good font for price display, fallback to default
        try:
            # Use Arial Bold for better readability and space utilization
            self.font = ImageFont.truetype("arialbd.ttf", 72)
        except:
            try:
                # Fallback to regular Arial
                self.font = ImageFont.truetype("arial.ttf", 72)
            except:
                try:
                    self.font = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
                except:
                    # Fallback to default font
                    self.font = ImageFont.load_default()

        logger.info(f"PriceDisplay initialized: {width}x{height}, {self.rows} rows")

    def generate_price_image(self, prices, output_path="price_display.png"):
        """Generate PNG image with price layout

        Args:
            prices: List of 5 price strings (e.g., ["1500", "1400", "1300", "1200", "1100"])
            output_path: Path to save the generated image

        Returns:
            str: Path to generated image file
        """
        if len(prices) != self.rows:
            logger.warning(f"Expected {self.rows} prices, got {len(prices)}. Adjusting...")
            # Pad or truncate to match expected rows
            if len(prices) < self.rows:
                prices.extend(["0"] * (self.rows - len(prices)))
            else:
                prices = prices[:self.rows]

        # Create new image with black background
        image = Image.new('RGB', (self.width, self.height), self.colors['background'])
        draw = ImageDraw.Draw(image)

        # Draw each price row
        for row in range(self.rows):
            price = prices[row]
            y_start = row * self.row_height
            y_end = (row + 1) * self.row_height

            # Draw left side
            self._draw_price_cell(draw, price, 0, y_start, self.half_width, self.row_height)

            # Draw right side (duplicate)
            self._draw_price_cell(draw, price, self.half_width, y_start, self.half_width, self.row_height)

            # Draw horizontal separator line (except for last row)
            if row < self.rows - 1:
                separator_y = y_end - 1
                draw.line([(0, separator_y), (self.width, separator_y)],
                         fill=self.colors['border'], width=2)

        # Save the image
        try:
            image.save(output_path, 'PNG')
            logger.info(f"Price display image saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save price image: {str(e)}")
            return None

    def _draw_price_cell(self, draw, price, x, y, width, height):
        """Draw a single price cell with left/right duplication

        Args:
            draw: PIL ImageDraw object
            price: Price string to display
            x, y: Top-left coordinates
            width, height: Cell dimensions
        """
        # Add minimal padding for maximum text size
        padding = 5
        text_x = x + padding
        text_y = y + padding
        text_width = width - (2 * padding)
        text_height = height - (2 * padding)

        # Format price with commas if needed
        try:
            # Add commas for thousands
            numeric_price = int(price)
            formatted_price = f"{numeric_price:,}"
        except:
            formatted_price = price

        # Calculate font size to fit the cell
        font_size = self._calculate_font_size(formatted_price, text_width, text_height)
        try:
            cell_font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
            try:
                cell_font = ImageFont.truetype("arial.ttf", font_size)
            except:
                cell_font = self.font

        # Get text bounding box
        bbox = draw.textbbox((0, 0), formatted_price, font=cell_font)
        text_width_actual = bbox[2] - bbox[0]
        text_height_actual = bbox[3] - bbox[1]

        # Center the text in the cell
        text_x_centered = x + (width - text_width_actual) // 2
        text_y_centered = y + (height - text_height_actual) // 2

        # Draw main text (no shadow for cleaner look)
        draw.text((text_x_centered, text_y_centered),
                  formatted_price, font=cell_font, fill=self.colors['text'])

        # Draw cell border
        draw.rectangle([x, y, x + width - 1, y + height - 1],
                      outline=self.colors['border'], width=1)

    def _calculate_font_size(self, text, max_width, max_height):
        """Calculate optimal font size to fit text in given dimensions

        Args:
            text: Text to fit
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            int: Optimal font size
        """
        font_size = 24  # Start larger for better performance
        max_font_size = 120  # Maximum reasonable size for large display

        while font_size < max_font_size:
            try:
                test_font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                try:
                    test_font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    test_font = self.font

            bbox = self.font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            if text_width > max_width * 0.95 or text_height > max_height * 0.95:
                return max(12, font_size - 2)  # Step back if too big

            font_size += 2

        return min(font_size, max_font_size)

    def update_display(self, prices, output_path="price_display.png"):
        """Update the price display with new prices

        Args:
            prices: List of new prices
            output_path: Path to save updated image

        Returns:
            str: Path to updated image file
        """
        logger.info(f"Updating price display with {len(prices)} prices: {prices}")
        return self.generate_price_image(prices, output_path)

# Example usage and testing
if __name__ == "__main__":
    # Test the price display
    display = PriceDisplay(width=256, height=160)

    # Sample prices from docs.txt
    test_prices = ["1500", "1400", "1300", "1200", "1100"]

    # Generate test image
    output_file = display.generate_price_image(test_prices, "test_prices.png")
    print(f"Test image generated: {output_file}")