import re
import base64
from pathlib import Path
import logging # Import logging for consistency

logger = logging.getLogger(__name__) # Get logger instance

class ScribeFormatter:
    """
    Formats Pathfinder Scribe markdown into styled HTML for display.
    Encapsulates CSS styles and markdown parsing logic.
    """

    # ACTION_ICON_BASE_PATH will now be set dynamically in __init__
    # ACTION_SYMBOLS will be generated dynamically

    # Mapping for specific tag types to their CSS class suffixes
    TAG_CLASS_MAP = {
        "common": "common",
        "uncommon": "uncommon",
        "rare": "rare",
        "unique": "unique",
        "n": "align", "l": "align", "c": "align", "g": "align", "e": "align", # Alignments
        "small": "size", "medium": "size", "large": "size", "huge": "size", "gargantuan": "size", "tiny": "size" # Sizes
    }

    # The entire CSS block is now a class constant, without the <style> tags
    CSS_STYLES = """
        /* Global resets and base styles */
        *, ::after, ::before {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            line-height: inherit; /* Inherit line-height from parent or specific rules */
        }
        html {
            font-family: sans-serif;
            line-height: 1.15;
            -webkit-text-size-adjust: 100%;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
            font-size: 1rem;
            font-weight: 400;
            line-height: 1.5;
            color: #222;
            text-align: left;
            background-color: #fff;
        }
        :root, .pdf {
            font-size: 10.4pt;
            line-height: 1; /* Tight line-height for root, paragraphs will override */
        }
        :root {
            --blue: #64b7eb;
            --indigo: #6610f2;
            --purple: #6f42c1;
            --pink: #e83e8c;
            --red: #ee420c;
            --orange: #fd7e14;
            --yellow: #f5c525;
            --green: #22b2a3;
            --teal: #20c997;
            --cyan: #369;
            --white: #fff;
            --gray: #777;
            --gray-dark: #333;
            --primary: #64b7eb;
            --secondary: #eb648e;
            --success: #22b2a3;
            --info: #369;
            --warning: #f5c525;
            --danger: #ee420c;
            --light: #f8f9fa;
            --dark: #222;
            --breakpoint-xs: 0;
            --breakpoint-sm: 576px;
            --breakpoint-md: 768px;
            --breakpoint-lg: 992px;
            --breakpoint-xl: 1200px;
            --font-family-sans-serif: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
            --font-family-monospace: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }

        /* Custom scrollbar styles */
        *::-webkit-scrollbar {
            width: 10px;
            background-color: transparent;
        }
        *::-webkit-scrollbar-thumb {
            background-color: #bbb;
            border-radius: 0.25rem;
        }
        *::-webkit-scrollbar-track {
            border: none;
            background-color: transparent;
        }

        /* Font faces for specific styles */
        @font-face {
            font-family: "ff-good-web-pro";
            src: url(https://use.typekit.net/af/a92a50/00000000000000003b9b2727/27/l?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("woff2"), url(https://use.typekit.net/af/a92a50/00000000000000003b9b2727/27/d?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("woff"), url(https://use.typekit.net/af/a92a50/00000000000000003b9b2727/27/a?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("opentype");
            font-display: auto;
            font-style: normal;
            font-weight: 700;
        }
        @font-face {
            font-family: "ff-good-web-pro-condensed";
            src: url(https://use.typekit.net/af/64399a/00000000000000003b9b2727/27/l?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("woff2"), url(https://use.typekit.net/af/64399a/00000000000000003b9b2727/27/d?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("woff"), url(https://use.typekit.net/af/64399a/00000000000000003b9b2727/27/a?primer=7cdcb4429388b87d491567ad933fd320f658358d17d6c2e4&fvd=n7&v=3) format("opentype");
            font-display: auto;
            font-style: normal;
            font-weight: 700;
        }

        /* Scribe Stat Block specific styles */
        .scribe-stat-block {
            font-family: 'ff-good-web-pro', var(--font-family-sans-serif) !important;
            color: var(--gray-dark);
            background-color: var(--light);
            border: 1px solid #ccc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .scribe-header-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 10px;
        }
        .scribe-stat-block .scribe-name { /* Increased specificity */
            color: var(--dark);
            line-height: 1;
            margin: 0 !important; /* Added !important */
            text-transform: uppercase;
            font-size: 1.4rem !important; /* Added !important */
            padding-top: 0.1rem;
            font-weight: bold;
            font-family: 'ff-good-web-pro-condensed', var(--font-family-sans-serif) !important;
        }
        .scribe-stat-block .scribe-type-level { /* Increased specificity */
            color: var(--dark);
            text-align: right;
            line-height: 1;
            margin: 0 !important; /* Added !important */
            text-transform: uppercase;
            font-size: 1.4rem !important; /* Added !important */
            padding-top: 0.1rem;
            font-weight: bold;
            margin-top: -1.45rem !important;
            font-family: 'ff-good-web-pro-condensed', var(--font-family-sans-serif) !important;
        }
        .scribe-hr {
            margin-top: 0; /* Changed from 0.15rem */
            margin-bottom: 0; /* Changed from 0.15rem */
            border: 0;
            border-top: 1px solid rgba(0, 0, 0, 0.75);
            border-bottom: 1px solid rgba(0, 0, 0, 0.125);
            opacity: 0.75;
            box-sizing: content-box;
            height: 0;
            overflow: visible;
        }
        .traits {
            margin-top: 0.25rem;
            margin-bottom: 0.25rem;
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            align-items: center;
        }
        .pf-trait {
            font-family: 'ff-good-web-pro-condensed', 'Open Sans Condensed', sans-serif !important;
            background: #5d0000 !important;
            color: #fff !important;
            border-color: #d8c384 !important;
            display: inline-block;
            padding: 0.25rem 0.5rem 0.1rem 0.5rem;
            font-weight: bold;
            line-height: 1;
            text-transform: uppercase;
            font-size: 0.8rem;
            border-width: 0.15rem;
            border-style: solid;
            border-right-width: 0.1rem;
            border-left-width: 0.1rem;
            text-align: center;
            font-kerning: none;
            white-space: nowrap;
            border-radius: 0.25rem;
        }
        .pf-trait-edge {
            background-color: #d8c384 !important;
            width: 3px !important;
            display: inline-block !important;
            padding: 0.25rem 0 0.1rem 0;
            min-width: 0;
            overflow: hidden;
            vertical-align: top;
        }
        /* Specific tag colors - these need !important to override the default .pf-trait background */
        .pf-trait-common { background-color: var(--primary) !important; color: var(--white) !important; }
        .pf-trait-uncommon { background-color: #98503c !important; color: var(--white) !important; }
        .pf-trait-rare { background-color: var(--orange) !important; color: var(--white) !important; }
        .pf-trait-unique { background-color: var(--pink) !important; color: var(--white) !important; }

        /* Alignment tags */
        .pf-trait-align { background-color: #566193 !important; color: var(--white) !important; }

        /* Size tags */
        .pf-trait-size { background-color: #3a7a58 !important; color: var(--white) !important; }

        /* Paragraph and list item styling within the stat block */
        .scribe-stat-block p, .scribe-stat-block li {
            line-height: 1.4;
            text-align: justify;
            margin-block-start: 1em; /* Default paragraph spacing */
            margin-block-end: 1em;
            margin-inline-start: 0px;
            margin-inline-end: 0px;
            unicode-bidi: isolate;
        }

        /* Hanging indent for paragraphs */
        .scribe-stat-block p.hang {
            padding-left: 1em;
            text-indent: -1em;
            margin-top: 0.25rem; /* Smaller top margin for hanging paragraphs */
            margin-bottom: 0.25rem;
            line-height: 1.1; /* Slightly tighter line-height for hanging paragraphs */
        }

        /* Remove margin between consecutive hanging paragraphs within an item */
        .scribe-stat-block .item p.hang + p.hang {
            margin-top: 0 !important;
        }
        /* Remove margin between consecutive paragraphs within an item */
        .scribe-stat-block .item p + p {
            margin-top: 0;
        }

        /* General adjacent sibling margins for consistent vertical rhythm */
        .scribe-stat-block * + p,
        .scribe-stat-block * + h1,
        .scribe-stat-block * + h2,
        .scribe-stat-block * + h3,
        .scribe-stat-block * + h4,
        .scribe-stat-block * + h5,
        .scribe-stat-block * + h6,
        .scribe-stat-block * + table,
        .scribe-stat-block * + hr,
        .scribe-stat-block h1 + ul,
        .scribe-stat-block h2 + ul,
        .scribe-stat-block h3 + ul,
        .scribe-stat-block h4 + ul,
        .scribe-stat-block h5 + ul,
        .scribe-stat-block h6 + ul,
        .scribe-stat-block * + .content,
        .scribe-stat-block * + .item,
        .scribe-stat-block * + .note,
        .scribe-stat-block * + .rules,
        .scribe-stat-block * + .sample,
        .scribe-stat-block * + .info,
        .scribe-stat-block * + .math,
        .scribe-stat-block * + .right,
        .scribe-stat-block * + .left,
        .scribe-stat-block * + .p { /* .p is likely a custom class for paragraphs */
            margin-top: 1em; /* Default spacing between blocks */
        }

        /* Specific override for .item *+p to remove top margin if it was intentional */
        .scribe-stat-block .item *+p {
            margin-top: 0 !important;
        }

        /* Strong/bold styling */
        .scribe-stat-block b, .scribe-stat-block strong {
            font-weight: bolder;
        }

        /* Font family for specific elements within #result */
        #result .item, #result .note, #result .info {
            font-family: 'ff-good-web-pro' !important;
        }

        /* Action icon styling */
        .action-icon {
            height: 1em; /* Adjust as needed to fit text line-height */
            vertical-align: middle;
            margin-right: 0.1em;
        }
        
        /* Custom hr style for scribe-hr */
        .scribe-hr {
            margin: 0 !important;
        }
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.ACTION_SYMBOLS = self._generate_action_symbols()

    def _get_image_base64(self, image_name: str) -> str:
        """Reads an image file and returns its base64 encoded string."""
        image_path = self.root_dir / "data" / image_name
        if not image_path.exists():
            logger.warning(f"Image not found at {image_path}") # Changed from print to logger.warning
            return "" # Return empty string if image not found

        with open(image_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine MIME type based on extension
        if image_path.suffix == ".png":
            mime_type = "image/png"
        elif image_path.suffix == ".jpg" or image_path.suffix == ".jpeg":
            mime_type = "image/jpeg"
        elif image_path.suffix == ".svg":
            mime_type = "image/svg+xml"
        else:
            mime_type = "application/octet-stream" # Generic fallback

        return f"data:{mime_type};base64,{encoded_string}"

    def _generate_action_symbols(self) -> dict:
        """Generates the ACTION_SYMBOLS dictionary with base64 encoded image data."""
        symbols = {
            ":a:": "one-action.png",
            ":aa:": "two-action.png",
            ":aaa:": "three-action.png",
            ":r:": "reaction.png",
            ":f:": "free-action.png",
        }
        
        generated_symbols = {}
        for key, filename in symbols.items():
            base64_src = self._get_image_base64(filename)
            if base64_src:
                generated_symbols[key] = f'<img src="{base64_src}" class="action-icon" alt="{filename.split(".")[0].replace("-", " ").title()}">'
            else:
                generated_symbols[key] = f'<span>[{key}]</span>' # Fallback text if image not found
        return generated_symbols

    def format_markdown_to_html(self, markdown_text: str, display_name: str = "") -> str:
        """
        Formats Pathfinder Scribe markdown into styled HTML for display.

        Args:
            markdown_text (str): The Scribe Markdown content of the monster's stat block.
            display_name (str): The name of the monster to display in the header.
                                This will override any name found with '# ' in the markdown.

        Returns:
            str: HTML formatted string of the stat block.
        """
        processed_text = markdown_text
        for symbol, html_tag in self.ACTION_SYMBOLS.items():
            processed_text = processed_text.replace(symbol, html_tag)

        lines = processed_text.split('\n')
        html_content = []
        
        # Always attempt to parse H1 and H2 from the markdown lines first
        parsed_monster_name = ""
        parsed_monster_type_level = ""

        if lines and lines[0].strip().startswith('# '):
            parsed_monster_name = lines.pop(0).strip('# ').strip()
        
        if lines and lines[0].strip().startswith('## '):
            parsed_monster_type_level = lines.pop(0).strip('## ').strip()

        # Use display_name if provided, otherwise use the parsed name
        monster_name = display_name if display_name else parsed_monster_name
        monster_type_level = parsed_monster_type_level # display_name only overrides the main name

        # Construct the header row
        if monster_name or monster_type_level:
            header_html = '<div class="scribe-header-row">'
            if monster_name:
                header_html += f'<h1 class="scribe-name">{monster_name}</h1>'
            if monster_type_level:
                header_html += f'<h2 class="scribe-type-level">{monster_type_level}</h2>'
            header_html += '</div>'
            html_content.append(header_html)

        current_paragraph_lines = []

        def _flush_paragraph():
            nonlocal current_paragraph_lines
            if current_paragraph_lines:
                # Join lines with <br> and wrap in <p class="hang">
                html_content.append(f'<p class="hang">{"<br>".join(current_paragraph_lines)}</p>')
                current_paragraph_lines = []

        for line in lines:
            stripped_line = line.strip()

            if not stripped_line:
                _flush_paragraph()
                continue  # Skip empty lines

            # Line break
            if stripped_line == '-':
                _flush_paragraph()
                html_content.append('<hr class="scribe-hr">')
            # Tags
            elif stripped_line.startswith('; '):
                _flush_paragraph()
                tags_str = stripped_line[2:].strip()
                tags_html = []
                for tag in tags_str.split(','):
                    tag = tag.strip()
                    tag_lower = tag.lower()

                    # Use the TAG_CLASS_MAP for cleaner tag class assignment
                    tag_class_suffix = self.TAG_CLASS_MAP.get(tag_lower, "")

                    if tag_class_suffix:
                        tags_html.append(f'<div class="pf-trait pf-trait-{tag_class_suffix}">{tag}</div>')
                    else:
                        tags_html.append(f'<div class="pf-trait">{tag}</div>')
                html_content.append(f'<div class="traits">{"".join(tags_html)}</div>')
            # All other lines are treated as part of a paragraph block
            else:
                # Convert bold markdown to strong HTML
                line_to_add = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', line)
                current_paragraph_lines.append(line_to_add)

        _flush_paragraph()  # Flush any remaining paragraph lines at the end

        # Embed the CSS directly inside the main stat-block div
        return '<div class="scribe-stat-block">\n<style>' + self.CSS_STYLES + '\n</style>\n' + "\n".join(html_content) + '\n</div>'