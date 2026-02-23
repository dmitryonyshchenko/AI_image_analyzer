"""
Centralized site configuration.
Edit this file to update the footer text displayed on all pages of the site.
"""

SITE_CONFIG = {
    # Footer — displayed at the bottom of every page
    "footer_tagline": (
        "This is an AI capabilities demonstrator, developed entirely using prompt coding "
        "with Claude Sonnet 4.6 (claude.ai/code)."
    ),
    # GitHub URL — fill in when the project is published
    "footer_git_url": "https://github.com/dmitryonyshchenko/AI_image_analyzer",
    "footer_author": "Dmitry Onyshchenko",
    # Rough estimate of total prompt-engineering effort for the project
    "footer_effort": "~8 hours of prompt coding",
    "footer_model_note": (
        "This project uses free AI models and hosting by default. "
        "Speed and recognition quality may vary."
    ),
    # Presentation download link
    "footer_presentation_url": "/static/AI_Image_Analyzer_Presentation.pptx",
}
