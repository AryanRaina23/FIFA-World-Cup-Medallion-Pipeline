import os
import csv
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

def make_pretty_xml(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    src_dir = os.path.join(project_root, "FIFA Dataset")
    dest_dir = os.path.join(project_root, "data", "sources")
    
    os.makedirs(dest_dir, exist_ok=True)
    
    print(f"Reading from: {src_dir}")
    print(f"Writing to: {dest_dir}")
    
    # 1. wc_2026_fixtures.csv (keep as CSV)
    fixtures_src = os.path.join(src_dir, "wc_2026_fixtures.csv")
    fixtures_dest = os.path.join(dest_dir, "wc_2026_fixtures.csv")
    if os.path.exists(fixtures_src):
        with open(fixtures_src, 'r', encoding='utf-8') as f_in, open(fixtures_dest, 'w', newline='', encoding='utf-8') as f_out:
            f_out.write(f_in.read())
        print("Copied wc_2026_fixtures.csv")
    else:
        print("Warning: wc_2026_fixtures.csv not found!")

    # 2. wc_all_matches.csv (keep as CSV)
    matches_src = os.path.join(src_dir, "wc_all_matches.csv")
    matches_dest = os.path.join(dest_dir, "wc_all_matches.csv")
    if os.path.exists(matches_src):
        with open(matches_src, 'r', encoding='utf-8') as f_in, open(matches_dest, 'w', newline='', encoding='utf-8') as f_out:
            f_out.write(f_in.read())
        print("Copied wc_all_matches.csv")
    else:
        print("Warning: wc_all_matches.csv not found!")

    # 3. wc_2026_teams.csv (convert to JSON)
    teams_src = os.path.join(src_dir, "wc_2026_teams.csv")
    teams_dest = os.path.join(dest_dir, "wc_2026_teams.json")
    if os.path.exists(teams_src):
        teams_data = []
        with open(teams_src, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # convert fifa_rank to int if possible
                if row.get('fifa_rank'):
                    try:
                        row['fifa_rank'] = int(row['fifa_rank'])
                    except ValueError:
                        pass
                teams_data.append(row)
        with open(teams_dest, 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, indent=4)
        print("Converted wc_2026_teams.csv to JSON")
    else:
        print("Warning: wc_2026_teams.csv not found!")

    # 4. wc_top_scorers.csv (convert to JSON)
    scorers_src = os.path.join(src_dir, "wc_top_scorers.csv")
    scorers_dest = os.path.join(dest_dir, "wc_top_scorers.json")
    if os.path.exists(scorers_src):
        scorers_data = []
        with open(scorers_src, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # convert some numeric fields
                for num_col in ['edition', 'year', 'goals', 'assists', 'penalties', 'matches_played']:
                    if row.get(num_col):
                        try:
                            row[num_col] = int(row[num_col])
                        except ValueError:
                            pass
                scorers_data.append(row)
        with open(scorers_dest, 'w', encoding='utf-8') as f:
            json.dump(scorers_data, f, indent=4)
        print("Converted wc_top_scorers.csv to JSON")
    else:
        print("Warning: wc_top_scorers.csv not found!")

    # 5. wc_all_editions.csv (convert to XML)
    editions_src = os.path.join(src_dir, "wc_all_editions.csv")
    editions_dest = os.path.join(dest_dir, "wc_all_editions.xml")
    if os.path.exists(editions_src):
        root = ET.Element("editions")
        with open(editions_src, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ed_node = ET.SubElement(root, "edition")
                for key, val in row.items():
                    # Standardize XML tags to avoid spaces or special chars (though keys are already clean)
                    child = ET.SubElement(ed_node, key)
                    child.text = val
        
        pretty_xml = make_pretty_xml(root)
        with open(editions_dest, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        print("Converted wc_all_editions.csv to XML")
    else:
        print("Warning: wc_all_editions.csv not found!")

if __name__ == "__main__":
    main()
