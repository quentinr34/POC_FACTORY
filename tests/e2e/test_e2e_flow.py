from playwright.sync_api import expect, sync_playwright


def test_analyze_flow_and_history(base_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url)

        page.fill("#brief", "Le client souhaite refondre son portail RH avec integration SIRH.")
        page.click("#analyze-btn")

        result = page.locator("#result")
        expect(result).to_be_visible(timeout=15000)

        score = page.locator("#score").inner_text()
        assert score.isdigit()
        assert 0 <= int(score) <= 100

        expect(page.locator("#questions li")).to_have_count(3)

        history_rows = page.locator("#history > div")
        expect(history_rows.first).to_be_visible(timeout=10000)

        browser.close()
