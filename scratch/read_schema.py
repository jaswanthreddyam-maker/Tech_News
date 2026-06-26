with open("database/schema.sql", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_section(keyword, before=5, after=30):
    for idx, line in enumerate(lines):
        if keyword in line:
            print(f"--- MATCH: Line {idx+1} ---")
            start = max(0, idx - before)
            end = min(len(lines), idx + after)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].strip()}")

print("Searching for user_reading_history...")
print_section("CREATE TABLE public.user_reading_history")
print("\nSearching for articles table...")
print_section("CREATE TABLE public.articles")
