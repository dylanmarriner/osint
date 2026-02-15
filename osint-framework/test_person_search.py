#!/usr/bin/env python3
"""End-to-end test of PersonRecon with stealth session."""
import asyncio
import sys
import json
import time

sys.path.insert(0, "src")


async def main():
    # Direct import to avoid package-level relative import issues
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "person_recon", "src/connectors/local/person_recon.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    PersonRecon = mod.PersonRecon
    StealthSession = mod.StealthSession

    print("=" * 60)
    print("  OSINT Person Search — End-to-End Test")
    print("=" * 60)

    # --- Test 1: StealthSession basic connectivity ---
    print("\n[1/3] Testing StealthSession connectivity...")
    try:
        async with StealthSession() as stealth:
            resp = await stealth.get("https://httpbin.org/user-agent")
            if resp.status == 200:
                data = await resp.json()
                ua = data.get("user-agent", "unknown")
                print(f"  ✅ StealthSession works — UA: {ua[:60]}...")
            else:
                print(f"  ⚠️  Got status {resp.status}")
    except Exception as e:
        print(f"  ❌ StealthSession failed: {e}")

    # --- Test 2: StealthSession fingerprint consistency ---
    print("\n[2/3] Testing fingerprint consistency within session...")
    try:
        async with StealthSession() as stealth:
            agents = []
            for i in range(3):
                resp = await stealth.get("https://httpbin.org/headers")
                if resp.status == 200:
                    data = await resp.json()
                    ua = data["headers"].get("User-Agent", "")
                    agents.append(ua)
            if len(set(agents)) == 1:
                print(f"  ✅ Same fingerprint across 3 requests (consistent)")
            else:
                print(f"  ⚠️  Fingerprint varied: {agents}")
    except Exception as e:
        print(f"  ❌ Fingerprint test failed: {e}")

    # --- Test 3: Full person search with a public figure ---
    print("\n[3/3] Running full person search (Linus Torvalds — public figure)...")
    print("  This tests all 10 recon stages with stealth...")
    start = time.time()

    recon = PersonRecon()

    # Use a well-known public figure to guarantee results
    report = await recon.search(
        full_name="Linus Torvalds",
        location="Portland, Oregon"
    )

    elapsed = time.time() - start
    results = report.to_dict()

    print(f"\n  ⏱  Completed in {elapsed:.1f}s")
    print(f"  📊 Confidence score: {results.get('confidence_score', 0)}/100")
    print(f"  📡 Data sources hit: {results.get('data_sources', [])}")

    # Summarize findings
    sections = [
        ("social_profiles", "Social Profiles"),
        ("github_details", "GitHub Details"),
        ("possible_emails", "Possible Emails"),
        ("web_mentions", "Web Mentions"),
        ("public_records", "Public Records"),
        ("phone_numbers", "Phone Numbers"),
        ("addresses", "Addresses"),
        ("archived_pages", "Archived Pages"),
        ("breaches", "Breach Records"),
        ("employers", "Employers"),
        ("education", "Education"),
        ("relatives", "Relatives"),
    ]

    print("\n  📋 Results Summary:")
    found_any = False
    for key, label in sections:
        items = results.get(key, [])
        if items:
            found_any = True
            print(f"    • {label}: {len(items)} found")
            # Show first 2 items as preview
            for item in items[:2]:
                if isinstance(item, dict):
                    preview = item.get("platform") or item.get("url") or item.get("title") or item.get("source") or str(item)
                    print(f"      → {str(preview)[:80]}")
                else:
                    print(f"      → {str(item)[:80]}")

    gravatar = results.get("gravatar", {})
    if gravatar:
        found_any = True
        print(f"    • Gravatar: {gravatar.get('display_name', 'found')}")

    if not found_any:
        print("    ⚠️  No data found — stealth may be blocking or network issue")

    # Save full results to file for inspection
    output_file = "/tmp/person_search_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  💾 Full results saved to: {output_file}")

    print("\n" + "=" * 60)
    if found_any:
        print("  ✅ END-TO-END TEST PASSED")
    else:
        print("  ⚠️  TEST COMPLETED — no data returned (may need network)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
