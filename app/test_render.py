"""Test the gaps page renders correctly with auth."""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.utils.auth import create_session

app = create_app()
with app.app_context():
    client = app.test_client()
    user = User.query.filter_by(username='admin').first()
    token = create_session(user, ip='127.0.0.1')
    client.set_cookie('session_token', token, domain='localhost')

    # Test audit 5 (In_Progress)
    resp = client.get('/audits/5/gaps')
    print(f"Audit 5 gaps - Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.data.decode('utf-8')
        # Find a gap card with actions
        idx = data.find('data-criterion-code="MB3"')
        if idx > 0:
            print(data[idx:idx+1200])
        else:
            print("No gap card found for MB3")
            # Try finding any gap card
            idx2 = data.find('data-criterion-code=')
            if idx2 > 0:
                print(f"Found gap card at {idx2}:")
                print(data[idx2:idx2+1200])
            else:
                print("No gap cards found at all")
                # Print around the gaps-page div
                idx3 = data.find('gaps-page')
                if idx3 > 0:
                    print(data[idx3:idx3+2000])
    else:
        print(f"  Body: {resp.data[:500]}")

    # Test audit 4 (Completed - read-only)
    resp2 = client.get('/audits/4/gaps')
    print(f"\nAudit 4 gaps - Status: {resp2.status_code}")
    if resp2.status_code == 200:
        data2 = resp2.data.decode('utf-8')
        print(f"  Has action-item: {'action-item' in data2}")
        print(f"  Has read-only-val: {'read-only-val' in data2}")
        print(f"  Has btn-save (should be False): {'btn-save' in data2}")
