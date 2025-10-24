#!/usr/bin/env python3
"""
CLI Tool zum Parsen der Wikipedia-Listen von Bücherschränken und Export als CSV
"""
import requests
import csv
from bs4 import BeautifulSoup
import re


def get_wikipedia_lists():
    """Hole alle Wikipedia-Listen von Wikidata"""
    endpoint = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?item ?itemLabel ?article WHERE {
      ?item wdt:P361+ wd:Q19971565 .
      ?article schema:about ?item ;
               schema:inLanguage "de" ;
               schema:isPartOf <https://de.wikipedia.org/> .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "de" . }
    }
    """

    response = requests.get(
        endpoint,
        params={'query': query, 'format': 'json'},
        headers={'User-Agent': 'Buecherschrank/1.0'}
    )

    if response.status_code == 200:
        data = response.json()
        lists = []
        for item in data['results']['bindings']:
            lists.append({
                'label': item['itemLabel']['value'],
                'url': item['article']['value']
            })
        return lists
    return []


def parse_wikipedia_table(url, region):
    """Parse eine Wikipedia-Tabelle"""
    try:
        response = requests.get(url, headers={'User-Agent': 'Buecherschrank/1.0'})
        soup = BeautifulSoup(response.content, 'html.parser')

        # Finde alle Tabellen mit der Klasse "wikitable"
        tables = soup.find_all('table', class_='wikitable')

        buecherschraenke = []

        for table in tables:
            rows = table.find_all('tr')

            # Überspringe Header-Zeile
            for row in rows[1:]:
                cols = row.find_all(['td', 'th'])

                if len(cols) >= 6:  # Mind. 6 Spalten (Nr, Bild, Ausführung, Ort, Seit, Anmerkung, Lage)
                    # Extrahiere Koordinaten aus der Lage-Spalte
                    lage = ""
                    lage_col = cols[-1]  # Letzte Spalte ist "Lage"
                    coord_link = lage_col.find('a', class_='mw-kartographer-maplink')
                    if coord_link and 'data-lat' in coord_link.attrs:
                        lat = coord_link['data-lat']
                        lon = coord_link['data-lon']
                        lage = f"{lat}, {lon}"

                    buecherschrank = {
                        'region': region,
                        'nr': cols[0].get_text(strip=True),
                        # Spalte 1 (Bild) überspringen
                        'ausfuehrung': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                        'ort': cols[3].get_text(strip=True) if len(cols) > 3 else '',
                        'seit': cols[4].get_text(strip=True) if len(cols) > 4 else '',
                        'anmerkung': cols[5].get_text(strip=True) if len(cols) > 5 else '',
                        'lage': lage
                    }
                    buecherschraenke.append(buecherschrank)

        return buecherschraenke

    except Exception as e:
        print(f"Fehler beim Parsen von {url}: {e}")
        return []


def main():
    print("Schritt 1: Hole Wikipedia-Listen von Wikidata...")
    lists = get_wikipedia_lists()
    print(f"Gefunden: {len(lists)} Listen\n")

    all_buecherschraenke = []

    print("Schritt 2: Parse Wikipedia-Tabellen...")
    for i, list_item in enumerate(lists, 1):
        print(f"  [{i}/{len(lists)}] {list_item['label']}...")

        # Extrahiere Region aus dem Label
        region = list_item['label'].replace('Liste öffentlicher Bücherschränke in ', '')
        region = region.replace('Liste öffentlicher Bücherschränke im ', '')

        buecherschraenke = parse_wikipedia_table(list_item['url'], region)
        all_buecherschraenke.extend(buecherschraenke)
        print(f"       → {len(buecherschraenke)} Bücherschränke gefunden")

    print(f"\nSchritt 3: Exportiere {len(all_buecherschraenke)} Bücherschränke als CSV...")

    # Exportiere als CSV
    filename = 'buecherschraenke_deutschland.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['region', 'nr', 'ausfuehrung', 'ort', 'seit', 'anmerkung', 'lage']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')

        writer.writeheader()
        for item in all_buecherschraenke:
            writer.writerow(item)

    print(f"\n✓ Erfolgreich exportiert nach: {filename}")
    print(f"  Anzahl Einträge: {len(all_buecherschraenke)}")


if __name__ == "__main__":
    main()