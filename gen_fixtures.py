import os
from pathlib import Path

fixtures = {
    'class_actions_alberta': '<html><body><table><tr><td>Test v. Alberta Inc</td><td>2024-03-01</td></tr></table></body></html>',
    'class_actions_bc': '<html><body><div class="views-row">BC Corp vs. Smith 2024-03-01</div></body></html>',
    'class_actions_branch_macmaster': '<html><body><div class="post">Branch Macmaster v. Corp 2024-03-01</div></body></html>',
    'class_actions_cba': '<html><body><div class="record">CBA v. Entity 2024-03-01</div></body></html>',
    'class_actions_ca': '<html><body><div class="listing">ClassAction.ca v. Business 2024-03-01</div></body></html>',
    'class_actions_federal': '<html><body><table><tr><td>Federal v. Canada Ltd</td><td>2024-03-01</td></tr></table></body></html>',
    'class_actions_koskie': '<html><body><div class="case">Koskie Minsky v. Firm 2024-03-01</div></body></html>',
    'class_actions_merchant': '<html><body><div class="item">Merchant Law v. Shop 2024-03-01</div></body></html>',
    'class_actions_ontario': '<html><body><table><tr><td>Ontario v. Co 2024-03-01</td><td>2024-03-01</td></tr></table></body></html>',
    'class_actions_courtlistener': '{"results": [{"caseName": "US v. Canadian Corp Ltd.", "dateFiled": "2024-03-01", "absolute_url": "/cases/123/"}]}',
    'class_actions_quebec': '<html><body><div class="recours">Quebec v. Ville 2024-03-01</div></body></html>',
    'class_actions_siskinds': '<html><body><div class="proceedings">Siskinds v. Giant 2024-03-01</div></body></html>'
}

consumer_fixtures = {
    'consumer_bbb_complaints': '<html><body><div class="complaint">Bad Business v. User 2024-03-01</div></body></html>',
    'consumer_ccts_complaints': '<html><body><div class="decision">CCTS v. Telecom 2024-03-01</div></body></html>',
    'consumer_cpsc_recalls': '{"results": [{"title": "CPSC Recall", "url": "http://cpsc.gov/1"}]}',
    'consumer_health_canada_recalls': '<?xml version="1.0" encoding="UTF-8"?><rss><channel><item><title>Recall by Company X</title><description>Dangerous</description><pubDate>Wed, 01 Mar 2024 00:00:00 GMT</pubDate></item></channel></rss>',
    'consumer_obsi_decisions': '<html><body><div class="case">OBSI v. Bank 2024-03-01</div></body></html>',
    'consumer_opc_breach_reports': '<html><body><div class="breach">OPC v. Site 2024-03-01</div></body></html>',
    'consumer_provincial_privacy': '<html><body><div class="report">Provincial v. Agency 2024-03-01</div></body></html>',
    'consumer_transport_canada_recalls': '<html><body><div class="recall">Transport Canada v. Auto 2024-03-01</div></body></html>',
}

def generate_fixtures(base_dir, fixtures_dict):
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    for name, content in fixtures_dict.items():
        if 'cpsc' in name or 'courtlistener' in name:
            ext = 'json'
        elif 'health_canada' in name:
            ext = 'xml'
        else:
            ext = 'html'
        (base_path / f'{name}.{ext}').write_text(content, encoding='utf-8')

generate_fixtures('tests/fixtures/class_actions', fixtures)
generate_fixtures('tests/fixtures/consumer', consumer_fixtures)

print("Fixtures generated.")
