from app import app, db
from models import Material, MaterialVariant
import re

raw_data = '''
Bits & Disc

3M Sandpaper ₱18.00
#60
#80
#100
#120
#180
#220
#240
#280
#400
#1000

Twisted Wire Cup Brush 4" ₱120.00

Tyrolit Metal Cutting Disc 4" ₱84.00

Tyrolit Metal Cutting Disc 14" ₱630.00

Tailin Cutting Wheel 14″ ₱165.00

Tyrolit Ultra Thin Cutting Disc 4″ ₱105.00

Dormer Metal Drill Bit 1/8" ₱67.00

Tyrolit Metal Grinding 4" ₱110.00

KYK Metal Drill Bit ₱39.00 - ₱437.00
2.55mm	₱39.00
3mm	₱40.00
3.2mm	₱41.00
3.5mm	₱43.00
4mm	₱47.00
5mm	₱76.00
5.5mm	₱77.00
6mm	₱84.00
6.5mm	₱89.00
8mm	₱98.00
9.5mm	₱190.00
10mm	₱262.00
13mm	₱430.00

KYK Masonry Drill Bit ₱35.00 – ₱106.00
1/4"	₱48
1/2"	₱106
1/8"	₱35
3/8"	₱70
3/16"	₱40
5/16"	₱62
5/32"	₱37
9/32"	₱51

KYK Sharpening Stone 6" ₱55

Powercraft Metal Drill Bit ₱98.00 – ₱357.00 (CHECK)
1/4" 	₱98.00
1/2" 	₱357.00
3/8" 	₱171.00

PowerHouse Cup Brush Twisted ₱145.00

PowerHouse Diamond Cutting Wheel 4" ₱520.00

Buffing White 4 ₱30.00

Irwin Continuous Diamond Cutting Blade ₱375.00

Irwin Segmented Diamond Cutting Blade ₱341.00

Irwin turbo Diamond Cutting Blade ₱425.00

Bosch Masonry Drill Bit 10mm ₱63.00

KYK Diamond Wheel 4" ₱270.00 - ₱329.00
dry	₱270.00
wet	₱329.00

KYK Diamond Wheel Thin 4" ₱312.00

Maxsell TCT Circular Saw Blade ₱830.00 - ₱2,287.00
7" 	₱830.00
10" 	₱2,287.00

Lotus Hammer Drill Bit ₱292.00 - ₱446.00
12 x 260mm	₱292.00
18 x 200mm	₱446.00

KYK Hole Saw Set ₱191.00

Lotus Masonry Drill Bit ₱42.00 - ₱53.00

Irwin Masonry Drill Bit 3mm ₱80.00

Bosun Diamond Cutting Wheel 4" ₱234.00

Flap Discs ₱50.00

Tailin PVA Wheel ₱175.00 - ₱331.00
#60	₱175.00
#220	₱331.00
#1000	₱295.00

Lotus Hole Saw Set ₱293.00

Sanding Disc ₱18.00

Bosun TCT Circular Saw Blade 4" ₱249.00

KYK Depressed Center Metal ₱63.00

PowerHouse Diamond Cutting Wheel Ultra Thin 4" ₱364.00

Buffing Soap ₱300.00

HAND TOOLS

Adjustable Hacksaw ₱112.00

Handsaw ₱250.00

Hammer Wood Handle ₱190.00

Shovel All Steel Pointed ₱225.00

Shovel All Steel Square ₱212.00

Finishing Trowel ₱48.00

Utility Knife ₱63.00

Mansion Steel Brush ₱69.00

Bosch GST 700 Jigsaw ₱4,441.50

A-Ladder 6ft ₱1,480.00

A-Ladder 8ft ₱2,100.00

Measuring Tape 5m ₱100.00

Crow Bar 24" ₱231.00

Sealant Gun 9" ₱135.00

KYK Open Wrench Set 6-22mm ₱227.00

Tile Saw Cutter 16" ₱910.00

CONCRETING & MASONRY

Concrete Hollow Block ₱19.00 - ₱24.00

Eagle Cement Advance ₱225.00

Bistay per sack ₱35.00

Republic Cement ₱240.00

White Sand ₱27.00 - ₱2,000.00

Gravel 3/4 ₱75.00 - ₱2,000.00

Cement Trowel ₱55.00 - ₱95.00

Finishing Trowel ₱48.00

Concrete Buggy ₱4,524.00

Nylon String (tansi) ₱25.00 - ₱30.00

Chichibu White Cement ₱45.00

Crowbar 24" ₱231.00

Stanley Level Bar ₱490.00 - ₱780.00

Powerhouse Diamond Cutting Wheel 4" ₱520.00

Masonry Drill Bit 3mm ₱80.00

NAIL, TOX, & SCREWS

Black Pointed ₱1.00

Black Screw Metal ₱1.00 - ₱2.50
1" 	₱1
1-1/2" 	₱1
2" 	₱1
3" 	₱2.50

Tekscrew ₱2.00 - ₱3.00
3" Pointed	₱3
1" 	₱2
2" 	₱2
3" 	₱3

Hardiflex Screw 1" ₱1.00

Wood Screw Flat Head ₱1.00 - ₱10.00
6 x 1	₱1
6 x 2	₱2
7 x 1	₱1
8 x 1	₱1
14 x 4	₱10

Common Wire Nail ₱95.00 - ₱1,695.00 (₱95 per kilo)
1" 	₱1,695.00
1-1/2" 	₱1,625.00
1-1/4" 	₱1,695.00
2" 	₱1,625.00
3" 	₱1,625.00
4" 	₱1,625.00

Washer ₱1.60 – ₱5.00
6mm	₱1.60
8mm	₱2.50
10mm	₱5.00

Metal Screw Flat Head ₱1.02 – ₱15.00
8 x 2	₱1.00
10 x 4	₱8.00
12 x 3	₱4.00
14 x 1	₱6.00
14 x 3	₱15.00

Nuts ₱1.60 – ₱130.00
6mm	₱1.60
8mm	₱1.60
10mm	₱1.80
17mm	₱130

Hi-lo Screw ₱1.12 – ₱3.00
1" 	₱3.00
2" 	₱2.10
8 x 50	₱1.12

Wood Screw Pan Head ₱1.00 – ₱12.00
6 x 1	₱1.00
8 x 2	₱2.00
10 x 2	₱12.00

Wood Screw 12 x 3 ₱3.26

Metal Screw with Tox 1/8 x 1/2 ₱1.66

Pvc Clamp 1/2" ₱4.00

Utility Box Screw ₱1.50 – ₱3.51
2" 	₱1.50
3" 	₱3.51

Concealed Hinges Screw 1/2 ₱1.20

Concrete Nail ₱100.00

MDF Screw 7x32mm ₱0.45

PVC Coated Cup Hook ₱25.00 – ₱57.00
3/4" 	₱25.00
5/8" 	₱25.00
7/8" 	₱25.00
1" 	₱28.00
1-1/2" 	₱38.00
1-1/4" 	₱52.00
2" 	₱57.00

Bolt and Nut with washer 3/4 x 3/4 ₱6.40

Finishing Nail ₱98.00

Dyna Bolt ₱7.00 – ₱19.20
3/8 x 2	₱19.20
3/8 x 70mm	₱15.00
1/4 x 50mm	₱7.00

G.I Bolt and Nut 1/2 x 1 ₱10.80

Anchor Bolt with Nut 1/4 ₱90.71

Multi Drawer Cabinet ₱484.00

PowerHouse Screw Bilt Single 25 x 2 ₱60.00

G.I Threaded Rod 3/8 x 10" ₱112.00

Power Bit ₱100.80

PowerHouse Tek Screw Adaptor 48mm ₱29.12

U-Bolt Clamp ₱7.00 – ₱13.00
1/2" 	₱7.00
3/4" 	₱13.00
1" 	₱8.00

Expansion Shield ₱8.00

G.I Washer ₱2.58 – ₱5.02
1/2" 	₱5.02
3/8" 	₱2.58

G.I Nut ₱1.00 – ₱13.00
1/2" 	₱3.00
3/4" 	₱13.00
3/8" 	₱1.00

Wood Screw Brass ₱4.34 – ₱8.90
6 x 1	₱6.67
6 x 1/2	₱8.90
6 x 1-1/2	₱4.34

Nuts Stainless ₱1.62 – ₱4.22
1/4" 	₱1.62
3/8" 	₱4.22

Bolt ₱1.89 – ₱23.00
1/4 x 1	₱1.89
1/4 x 2	₱3.39
1/4 x 3	₱4.90
3/8 x 1 	₱4.40
3/8 x 2	₱7.82
3/8 x 3	₱12.00
5/16 x 1	₱3.07
5/16 x 2	₱5.42
5/16 x 3	₱23
6m x 25	₱2.75
6m x 35	₱3.28
6m x 50	₱4.14
6m x 65	₱5.17
6m x 75	₱5.63
8m x 25	₱5.17
8m x 35	₱6.03
8m x 50	₱8.03
8m x 65	₱9.30
8m x 75	₱9.49
10m x 25	₱7.44
10m x 35	₱8.48
10m x 50	₱11.00
10m x 65	₱13.00
10m x 75	₱14.00
1/4 x 1 x 1/2	₱2.6
1/4 x 2 x 1/2	₱4.15
3/8 x 1 x 1/2	₱6.15
3/8 x 2 x 1/2	₱9.50
5/16 x 1 x 1/2	₱4.65
5/16 x 2 x 1/2	₱6.60

Loop Hanger 1/2 ₱28.80

L-Bracket (Suction Cup) ₱12.00

Butterfly Screw Bit Double ₱30.00

Eye Bolt 1/2 x 8 ₱89.00

WOOD PRODUCTS

Coco Lumber ₱86.00 – ₱250.00
2 x 3 x 8	₱125.00
2 x 2 x 8	₱86.00
2 x 2 x 10	₱105.00
2 x 2 x 12	₱125.00
2 x 3 x 10	₱156.00
2 x 3 x 12	₱187.00
2 x 4 x 12	₱250.00

Good Lumber S4S ₱56.00 – ₱2,142.00
2 x 4 x 10	₱765.00
1/2 x 1 x 8	₱56.00
1/2 x 1 x 10	₱70.00
1/2 x 1 x 12	₱83.00
1/2 x 2 x 8	₱79.00
1/2 x 2 x 10	₱98.00
1/2 x 2 x 12	₱118.00
1 x 1-1/2 x 10	₱130.00
1 x 1 x 8	₱79.00
1 x 1 x 10	₱98.00
1 x 1 x 12	₱118.00
1 x 2 x 8	₱149.00
1 x 2 x 10	₱186.00
1 x 2 x 12	₱224.00
2 x 1-1/2 x 12	₱298.00
2 x 2 x 8	₱298.00
2 x 2 x 10	₱372.00
2 x 2 x 12	₱446.00
2 x 3 x 8	₱446.00
2 x 3 x 10	₱558.00
2 x 3 x 12	₱670.00
2 x 4 x 8	₱612.00
2 x 4 x 12	₱918.00
2 x 12 x 8	₱918.00

Marine Plywood ₱400.00 – ₱1,150.00
1/4" 	₱400.00
1/2" 	₱645.00
3/4" 	₱1,150.00

Plywood Ordinary ₱295.00 – ₱985.00
1/4" 	₱295.00
1/2" 	₱540.00
3/4" 	₱985.00

Phenolic Board 1/2 Croco ₱685.00

Phenolic Board 18mm ₱945.00

KD S4S Wood PL ₱212.00 – ₱331.25
1 x 1-1/2 x 12	₱212.00
2 x 3 x 8	₱230.00
2 x 3 x 12	₱331.25

Baseboard ₱251.00 – ₱504.00
1 x 3 x 8	₱251.00
1 x 4 x 8	₱336.00
1 x 4 x 10	₱420.00
1 x 4 x 12	₱504.00

Corneza 1 x 3 x 8 ₱262.00

Hardiflex Senepa 10in x 8ft x 9mm ₱288.00

Plyboard 3/4 ₱1,270.00

REBARS & G.I WIRES

Deformed Bar G33 ₱114.00 – ₱1,236.00
8mm	₱114.00
10mm	₱204.00
12mm	₱288.00
16mm	₱504.00
20mm	₱786.00
25mm	₱1,236.00

Deformed Bar G40 ₱180.00 – ₱675.00
10mm	₱180.00
10.5mm	₱420.00
12mm	₱279.00
16mm	₱437.00
20mm	₱675.00

GI Wire #16 ₱85.00 – ₱1,050.00
Kilo	₱1,050.00
Roll	₱85.00

Tyrolit Metal Cutting Disc ₱83.78 – ₱630.00
4"	₱83.78
14"	₱630.00

Tailin Cutting Wheel 14″ ₱165.00

Tyrolit Ultra Thin Cutting Disc 4″ ₱105.00

Tyrolit Metal Grinding Disc 4″ ₱110.00

Sandflex Handsaw Blade ₱45.00 – ₱50.00
18-TPI	₱45.00
24-TPI	₱50.00

DRYWALL & CEILING

W-Clip ₱5.00

Metal Furring
₱115.00 – ₱135.00

Shadow Line
₱120.00 – ₱150.00

Wall Angle
₱40.00 – ₱50.00

Carrying Channel
₱95.00 – ₱130.00

Metal Studs
₱115.00 – ₱175.00

Metal Tracks
₱95.00 – ₱190.00

Gardner
₱385.00 – ₱1,375.00

Blind Rivet
₱290.00 – ₱350.00

Gypsum Board MR 12mm
₱875.00

Ceiling Manhole Steel White 60 x 60
₱1,800.00

Stanley 14-563 Straight Cut Aviation Snips
₱426.00

Gypsum Board Knauf
₱500.00 – ₱550.00

KYK Aviation Snip Straight
₱262.00

Tin Snip Ordinary
₱340.00

Stanley Riveter Chrome
₱570.00
'''

CATEGORY_RE = re.compile(r'^[A-Z0-9 &.\-\']+$')
PRICE_RE = re.compile(r'\s*₱([\d,]+(?:\.\d+)?)')


def parse_price(price_text):
    price_text = price_text.replace('₱', '').replace(',', '').strip()
    try:
        return float(price_text)
    except ValueError:
        return 0.0


def add_material(name, category, price):
    existing = Material.query.filter_by(name=name).first()
    if existing:
        print(f"skipping existing: {name}")
        return existing

    material = Material(
        name=name,
        category=category,
        quantity=0,
        unit='pcs',
        reorder_point=0,
        price_per_unit=price
    )
    db.session.add(material)
    db.session.commit()
    print(f"added material: {name} ({category}) @ {price}")
    return material


def add_variant(material, variant_name, price):
    existing = MaterialVariant.query.filter_by(
        material_id=material.id, name=variant_name).first()
    if existing:
        return existing

    variant = MaterialVariant(
        material_id=material.id,
        name=variant_name,
        quantity=0,
        unit=material.unit,
        price=price
    )
    db.session.add(variant)
    db.session.commit()
    return variant


def main():
    current_category = None
    current_material = None

    for raw_line in raw_data.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.isupper() and len(line) < 50:
            current_category = line.title()
            current_material = None
            continue

        # Detect primary product line with price or price range
        if '₱' in line and '\t' not in line:
            # line like '3M Sandpaper ₱18.00' or 'KYK Metal Drill Bit ₱39.00 - ₱437.00'
            parts = line.split('₱')
            item = parts[0].strip()
            if not item:
                continue
            # primary price capture first amount
            price_part = '₱' + parts[1]
            price_to_parse = price_part.split('-')[0].strip()
            price = parse_price(price_to_parse)

            current_material = add_material(
                item, current_category or 'Uncategorized', price)
            continue

        # variant or size lines
        if current_material and '₱' in line:
            piece = line.replace('\t', ' ').strip()
            if not piece:
                continue
            # expected e.g. '2.55mm    ₱39.00' or '#60    ₱175.00'
            y = piece.split('₱')
            variant_name = y[0].strip()
            price_val = parse_price('₱' + y[1]) if len(y) > 1 else 0.0
            if variant_name:
                add_variant(current_material, variant_name, price_val)
            continue

    print('Import done.')


if __name__ == '__main__':
    with app.app_context():
        main()
