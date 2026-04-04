import re

from app import Material, MaterialVariant, app, db


SEED_TEXT = r"""


3M Sandpaper ₱18.00 (150pcs, 25 reorder point) (category: Bits & Disc)
60
80
100
120
180
220
240
280
400
1000

Twisted Wire Cup Brush 4" ₱120.00 (15pcs, 5 reorder point) (category: Bits & Disc)

Tyrolit Metal Cutting Disc 4" ₱84.00 (15pcs, 5 reorder point) (category: Bits & Disc)


Tyrolit Metal Cutting Disc 14" ₱630.00 (15pcs, 5 reorder point) (category: Bits & Disc)


Tailin Cutting Wheel 14″ ₱165.00 (15pcs, 5 reorder point) (category: Bits & Disc)


Tyrolit Ultra Thin Cutting Disc 4″ ₱105.00 (15pcs, 5 reorder point) (category: Bits & Disc)


Dormer Metal Drill Bit 1/8" ₱67.00 (25pcs, 5 reorder point) (category: Bits & Disc)


Tyrolit Metal Grinding 4" ₱110.00 (15pcs, 5 reorder point) (category: Bits & Disc)


KYK Metal Drill Bit ₱39.00 - ₱437.00 (5 reorder point) (category: Bits & Disc)

2.55mm	₱39.00 (15pcs)
3mm	₱40.00 (15pcs)
3.2mm	₱41.00 (15pcs)
3.5mm	₱43.00 (15pcs)
4mm	₱47.00 (15pcs)
5mm	₱76.00 (15pcs)
5.5mm	₱77.00 (15pcs)
6mm	₱84.00 (15pcs)
6.5mm	₱89.00 (15pcs)
8mm	₱98.00 (15pcs)
9.5mm	₱190.00 (15pcs)
10mm	₱262.00 (15pcs)
13mm	₱430.00 (15pcs)


KYK Masonry Drill Bit ₱35.00 – ₱106.00 (5 reorder point) (category: Bits & Disc)
1/4"	₱48 (15pcs)
1/2"	₱106 (15pcs)
1/8"	₱35 (15pcs)
3/8"	₱70 (15pcs)
3/16"	₱40 (15pcs)
5/16"	₱62 (15pcs)
5/32"	₱37 (15pcs)
9/32"	₱51 (15pcs)

KYK Sharpening Stone 6" ₱55 (category: Bits & Disc)

Powercraft Metal Drill Bit ₱98.00 – ₱357.00 (5 reorder point) (category: Bits & Disc)
1/4"	₱98.00 (15pcs)
1/2"	₱357.00 (15pcs)
3/8"	₱171.00 (15pcs)

PowerHouse Cup Brush Twisted ₱145.00 (15pcs, 5 reorder point) (category: Bits & Disc)


PowerHouse Diamond Cutting Wheel 4" ₱520.00 (15pcs, 5 reorder point) (category: Bits & Disc)

Buffing White 4 ₱30.00 (15pcs, 5 reorder point) (category: Bits & Disc)

Irwin Continuous Diamond Cutting Blade ₱375.00 (30pcs, 15 reorder point) (category: Bits & Disc)

Irwin Segmented Diamond Cutting Blade ₱341.00 (30pcs, 15 reorder point) (category: Bits & Disc)

Irwin turbo Diamond Cutting Blade ₱425.00 (30pcs, 15 reorder point) (category: Bits & Disc)

Bosch Masonry Drill Bit 10mm ₱63.00 (15pcs, 5 reorder point) (category: Bits & Disc)

KYK Diamond Wheel 4" ₱270.00 - ₱329.00 (15pcs each, 5 reorder point) (category: Bits & Disc)
dry	₱270.00 
wet	₱329.00

KYK Diamond Wheel Thin 4" ₱312.00 (20pcs, 5 reorder point) (category: Bits & Disc)

Maxsell TCT Circular Saw Blade ₱830.00 - ₱2,287.00 (20pcs each, 5 reorder point) (category: Bits & Disc)
7"	₱830.00
10"	₱2,287.00

Lotus Hammer Drill Bit ₱292.00 - ₱446.00 (15pcs each, 5 reorder point) (category: Bits & Disc)
12 x 260mm	₱292.00
18 x 200mm	₱446.00

KYK Hole Saw Set ₱191.00 (15pcs each, 5 reorder point) (category: Bits & Disc)

Lotus Masonry Drill Bit ₱42.00 - ₱53.00 (15pcs each, 5 reorder point) (category: Bits & Disc)
7/64 – 3mm ₱53.00
1/4 – 6mm ₱42.00

Irwin Masonry Drill Bit 3mm ₱80.00 (15pcs each, 5 reorder point) (category: Bits & Disc)

Bosun Diamond Cutting Wheel 4" ₱234.00 (15pcs each, 5 reorder point) (category: Bits & Disc)

Flap Discs ₱50.00 (30pcs each, 10 reorder point) (category: Bits & Disc)

Tailin PVA Wheel ₱175.00 - ₱331.00 (15pcs each, 5 reorder point) (category: Bits & Disc)
60	₱175.00
220	₱331.00
1000	₱295.00

Lotus Hole Saw Set ₱293.00 (15pcs each, 5 reorder point) (category: Bits & Disc)

Sanding Disc ₱18.00 (50pcs, 5 reorder point) (category: Bits & Disc)

Bosun TCT Circular Saw Blade 4" ₱249.00 (15pcs each, 5 reorder point) (category: Bits & Disc)

KYK Depressed Center Metal ₱63.00 (50pcs, 5 reorder point) (category: Bits & Disc)

PowerHouse Diamond Cutting Wheel Ultra Thin 4" ₱364.00 (50pcs, 5 reorder point) (category: Bits & Disc)

Buffing Soap ₱300.00 (20pcs, 5 reorder point) (category: Bits & Disc)





Adjustable Hacksaw ₱112.00 (10pcs, 5 reorder point) (category: Hand Tools)

Handsaw ₱250.00 (20pcs, 5 reorder point) (category: Hand Tools)

Hammer Wood Handle ₱190.00 (10pcs, 5 reorder point) (category: Hand Tools)

Shovel All Steel Pointed ₱225.00 (10pcs, 5 reorder point) (category: Hand Tools)

Shovel All Steel Square ₱212.00 (10pcs, 5 reorder point) (category: Hand Tools)

Finishing Trowel ₱48.00 (10pcs, 5 reorder point) (category: Hand Tools)

Utility Knife ₱63.00 (10pcs, 5 reorder point) (category: Hand Tools)

Mansion Steel Brush ₱69.00 (10pcs, 5 reorder point) (category: Hand Tools)

Bosch GST 700 Jigsaw ₱4,441.50 (5pcs, 2 reorder point) (category: Hand Tools)

A-Ladder 6ft ₱1,480.00 (8pcs, 5 reorder point) (category: Hand Tools)

A-Ladder 8ft ₱2,100.00 (8pcs, 5 reorder point) (category: Hand Tools)

Measuring Tape 5m ₱100.00 (10pcs, 5 reorder point) (category: Hand Tools)

Crow Bar 24" ₱231.00 (8pcs, 5 reorder point) (category: Hand Tools)

Sealant Gun 9" ₱135.00 (8pcs, 5 reorder point) (category: Hand Tools)

KYK Open Wrench Set 6-22mm ₱227.00 (8pcs, 5 reorder point) (category: Hand Tools)

Tile Saw Cutter 16" ₱910.00 (8pcs, 5 reorder point) (category: Hand Tools)






Concrete Hollow Block ₱23.00 - ₱32.00 (9999pcs each, 1000 reorder point) (category: Concreting & Masonry)
4" ₱23.00 
5" ₱25.00
6" ₱32.00

Eagle Cement Advance ₱225.00 (300pcs, 50 reorder point) (category: Concreting & Masonry)

Bistay per sack ₱35.00 (9999pcs, 1000 reorder point) (category: Concreting & Masonry)

Republic Cement ₱240.00 (9999pcs, 1000 reorder point) (category: Concreting & Masonry)

White Sand (600pcs, 50 reorder point) (category: Concreting & Masonry)
Sack ₱40.00

Gravel 3/4 (600pcs, 50 reorder point) (category: Concreting & Masonry)
Sack ₱80.00

Cement Trowel (15pcs, 5 reorder point) (category: Concreting & Masonry) 
6" ₱55.00
7" ₱82.00
8" ₱95.00

Finishing Trowel ₱48.00 (15pcs each, 5 reorder point) (category: Concreting & Masonry)

Concrete Buggy ₱4,524.00 (15pcs each, 5 reorder point) (category: Concreting & Masonry)

Nylon String (tansi) (15pcs each, 5 reorder point) (category: Concreting & Masonry)
70 ₱25.00
100 ₱30.00

Chichibu White Cement ₱45.00 (9999pcs each, 1000 reorder point) (category: Concreting & Masonry)

Crowbar 24" ₱231.00 (8pcs each, 3 reorder point) (category: Concreting & Masonry)

Stanley Level Bar (10pcs each, 3 reorder point) (category: Concreting & Masonry)
18" ₱490.00
36" ₱780.00

Powerhouse Diamond Cutting Wheel 4" ₱520.00 (15pcs each, 5 reorder point) (category: Concreting & Masonry)

Masonry Drill Bit 3mm ₱80.00 (10pcs each, 3 reorder point) (category: Concreting & Masonry)



Black Pointed ₱1.00 (800pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Black Screw Metal (400pcs each, 70 reorder point) (category: Nail, Tox, & Screws)
1"	₱1
1-1/2"	₱1
2"	₱1
3" 	₱2.50

Tekscrew (400pcs each, 40 reorder point) (category: Nail, Tox, & Screws)
3" Pointed	₱3
1"	₱2
2"	₱2
3"	₱3

Hardiflex Screw 1" ₱1.00 (800pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Wood Screw Flat Head (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
6 x 1	₱1
6 x 2	₱2
7 x 1	₱1
8 x 1	₱1
14 x 4	₱10

Common Wire Nail Box ₱1,695.00 (100pcs each, 20 reorder point) (category: Nail, Tox, & Screws)
1"	₱1,695.00 
1-1/2"	₱1,625.00
1-1/4"	₱1,695.00
2"	₱1,625.00
3"	₱1,625.00
4"	₱1,625.00

Washer (300pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
6mm	₱1.60
8mm	₱2.50
10mm	₱5.00

Metal Screw Flat Head (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
8 x 2	₱1.00
10 x 4	₱8.00
12 x 3	₱4.00
14 x 1	₱6.00
14 x 3	₱15.00

Nuts (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
6mm	₱1.60
8mm	₱1.60
10mm	₱1.80
17mm	₱130

Hi-lo Screw (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
1"	₱3.00
2"	₱2.10
8 x 50	₱1.12

Wood Screw Pan Head (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
6 x 1	₱1.00
8 x 2	₱2.00
10 x 2	₱12.00

Wood Screw 12 x 3 ₱3.26 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Metal Screw with Tox 1/8 x 1/2 ₱1.66 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Pvc Clamp 1/2" ₱4.00 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Utility Box Screw (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)
2"	₱1.50
3"	₱3.51

Concealed Hinges Screw 1/2 ₱1.20 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

Concrete Nail ₱100.00 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

MDF Screw 7x32mm ₱0.45 (400pcs each, 80 reorder point) (category: Nail, Tox, & Screws)

PVC Coated Cup Hook (150pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
3/4"	₱25.00
5/8"	₱25.00
7/8"	₱25.00
1"	₱28.00
1-1/2"	₱38.00
1-1/4"	₱52.00
2"	₱57.00

Bolt and Nut with washer 3/4 x 3/4 ₱6.40 (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Finishing Nail ₱98.00 (200pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Dyna Bolt (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
3/8 x 2		₱19.20
3/8 x 70mm	₱15.00
1/4 x 50mm	₱7.00

G.I Bolt and Nut 1/2 x 1 ₱10.80 (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Anchor Bolt with Nut 1/4 ₱90.71 (200pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Multi Drawer Cabinet ₱484.00 (7pcs each, 2 reorder point) (category: Nail, Tox, & Screws)

PowerHouse Screw Bilt Single 25 x 2 ₱60.00 (100pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

G.I Threaded Rod 3/8 x 10" ₱112.00 (150pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Power Bit ₱100.80 (100pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

PowerHouse Tek Screw Adaptor 48mm ₱29.12 (150pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

U-Bolt Clamp (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
1/2"	₱7.00
3/4"	₱13.00
1"	₱8.00

Expansion Shield ₱8.00 (150pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

G.I Washer (450pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
1/2"	₱5.02
3/8"	₱2.58

G.I Nut (450pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
1/2"	₱3.00
3/4"	₱13.00
3/8"	₱1.00

Wood Screw Brass (450pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
6 x 1		₱6.67
6 x 1/2		₱8.90
6 x 1-1/2	₱4.34

Nuts Stainless (450pcs each, 100 reorder point) (category: Nail, Tox, & Screws)
1/4"	₱1.62
3/8"	₱4.22

Bolt (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)
1/4 x 1		₱1.89
1/4 x 2		₱3.39
1/4 x 3		₱4.90
3/8 x 1 	₱4.40
3/8 x 2		₱7.82
3/8 x 3		₱12.00
5/16 x 1	₱3.07
5/16 x 2	₱5.42
5/16 x 3	₱23
6m x 25		₱2.75
6m x 35		₱3.28
6m x 50		₱4.14
6m x 65		₱5.17
6m x 75		₱5.63
8m x 25		₱5.17
8m x 35		₱6.03
8m x 50		₱8.03
8m x 65		₱9.30
8m x 75		₱9.49
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

Loop Hanger 1/2 ₱28.80 (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

L-Bracket (Suction Cup) ₱12.00 (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)

Butterfly Screw Bit Double ₱30.00 (100pcs each, 30 reorder point) (category: Nail, Tox, & Screws)

Eye Bolt 1/2 x 8 ₱89.00 (250pcs each, 50 reorder point) (category: Nail, Tox, & Screws)



Coco Lumber (400pcs each, 50 reorder point) (category: Wood Products)
2 x 3 x 8	₱125.00
2 x 2 x 8	₱86.00
2 x 2 x 10	₱105.00
2 x 2 x 12	₱125.00
2 x 3 x 10	₱156.00
2 x 3 x 12	₱187.00
2 x 4 x 12	₱250.00

Good Lumber S4S (400pcs each, 50 reorder point) (category: Wood Products)
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

Marine Plywood (350pcs each, 50 reorder point) (category: Wood Products)
1/4"	₱400.00
1/2"	₱645.00
3/4"	₱1,150.00

Plywood Ordinary (350pcs each, 50 reorder point) (category: Wood Products)
1/4"	₱295.00
1/2"	₱540.00
3/4"	₱985.00

Phenolic Board 1/2 Croco ₱685.00 (400pcs each, 50 reorder point) (category: Wood Products)

Phenolic Board 18mm ₱945.00 (400pcs each, 50 reorder point) (category: Wood Products)

KD S4S Wood PL (400pcs each, 50 reorder point) (category: Wood Products)
1 x 1-1/2 x 12	₱212.00
2 x 3 x 8	₱230.00
2 x 3 x 12	₱331.25

Baseboard (100pcs each, 30 reorder point) (category: Wood Products)
1 x 3 x 8	₱251.00
1 x 4 x 8	₱336.00
1 x 4 x 10	₱420.00
1 x 4 x 12	₱504.00

Corneza 1 x 3 x 8 ₱262.00 (100pcs each, 30 reorder point) (category: Wood Products)


Plyboard 3/4 ₱1,270.00 (500pcs each, 30 reorder point) (category: Wood Products)





Deformed Bar G33 (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
8mm	₱114.00
10mm	₱204.00
12mm	₱288.00
16mm	₱504.00
20mm	₱786.00
25mm	₱1,236.00

Deformed Bar G40 (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
10mm	₱180.00
10.5mm	₱420.00
12mm	₱279.00
16mm	₱437.00
20mm	₱675.00

GI Wire 16 (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
Kilo	₱1,050.00
Roll	₱85.00

Tyrolit Metal Cutting Disc (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
4"	₱83.78
14"	₱630.00

Tailin Cutting Wheel 14″ ₱165.00 (50pcs each, 30 reorder point) (category: Rebars & G.I Wires)

Tyrolit Ultra Thin Cutting Disc 4″ ₱105.00 (50pcs each, 30 reorder point) (category: Rebars & G.I Wires)

Tyrolit Metal Grinding Disc 4″ ₱110.00 (50pcs each, 30 reorder point) (category: Rebars & G.I Wires)

Sandflex Handsaw Blade  (50pcs each, 30 reorder point) (category: Rebars & G.I Wires)
18-TPI	₱45.00
24-TPI	₱50.00


DRYWALL & CEILING

W-Clip ₱5.00 (300pcs each, 30 reorder point) (category: Rebars & G.I Wires)


Shadow Line (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
1" x1" x 0.4mm x 3M ₱120.00
1" x1" x 0.5mm x 3M ₱150.00

Wall Angle (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
10ft. ₱50.00
8ft. ₱40.00

Carrying Channel (1000pcs each, 50 reorder point) (category: Rebars & G.I Wires)
0.5mm x 12mm x 38mm x 5M ₱95.00
0.8mm x 12mm x 38mm x 5M ₱130.00

Metal Studs (200pcs each, 30 reorder point) (category: Rebars & G.I Wires)
0.4mm x 100mm x 32mm x 2.4M	₱140.00
0.4mm x 100mm x 32mm x 3M	₱175.00
0.4mm x 75mm x 32mm x 3M	₱115.00
0.5mm x 100mm x 32mm x 3M	₱153.00
0.5mm x 75mm x 32mm x 3M	₱135.00

Metal Tracks (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
0.8mm x 12 x 38 x 5mm	₱130.00
0.8mm x 5mm		₱190.00
12mm x 38mm x 0.5mm	₱95.00

Gardner (100pcs each, 30 reorder point) (category: Rebars & G.I Wires)
3.5mm	₱385.00
4.5mm	₱460.00
6mm	₱640.00
9mm	₱1,000.00
12mm 	₱1,375.00

Blind Rivet (50pcs each, 15 reorder point) (category: Rebars & G.I Wires)
Blind Rivet 1/8 x 1	₱350.00
Blind Rivet 1/8 x 1/2	₱290.00
Blind Rivet 1/8 x 3/4	₱300.00

Gypsum Board Knauf (50pcs each, 10 reorder point) (category: Rebars & G.I Wires)
9mm	₱560.00
12mm	₱615.00

Ceiling Manhole Steel White 60 x 60 (150pcs each, 40 reorder point) (category: Rebars & G.I Wires)
₱1,800.00

Stanley 14-563 Straight Cut Aviation Snips (20pcs each, 7 reorder point) (category: Rebars & G.I Wires)
₱426.00


KYK Aviation Snip Straight (15pcs each, 7 reorder point) (category: Rebars & G.I Wires)
₱262.00

Tin Snip Ordinary (15pcs each, 7 reorder point) (category: Rebars & G.I Wires)
₱340.00

Stanley Riveter Chrome (10pcs each, 4 reorder point) (category: Rebars & G.I Wires)
₱570.00


""".strip()


CATEGORY = "Bits & Disc"
DEFAULT_UNIT = "pcs"


def _normalize_name(s: str) -> str:
    s = s.strip()
    # Normalize “fancy” quotes to ascii for consistent matching.
    s = s.replace("″", '"').replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    return s


def _parse_number(num: str) -> float:
    num = num.replace(",", "").strip()
    return float(num)


def _extract_first_price(text: str) -> float | None:
    m = re.search(r"₱\s*([\d,]+(?:\.\d+)?)", text)
    if not m:
        return None
    return _parse_number(m.group(1))


def _extract_reorder_point(header: str) -> float | None:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*reorder point", header, flags=re.IGNORECASE)
    if not m:
        return None
    return _parse_number(m.group(1))


def _extract_qty_and_each(header: str) -> tuple[float | None, bool]:
    """
    Returns (qty, is_each).
    Looks for patterns like:
      (15pcs, 5 reorder point)
      (15pcs each, 5 reorder point)
      (9999pcs each, 1000 reorder point)
    """
    paren = header[header.find("(") : header.rfind(")")] if "(" in header and ")" in header else header
    is_each = "each" in paren.lower()
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*pcs", paren, flags=re.IGNORECASE)
    if not m:
        return None, is_each
    return _parse_number(m.group(1)), is_each


def _parse_variant_line(line: str) -> tuple[str, float | None] | None:
    """
    Parses variant lines like:
      "#60" (price inherited from header)
      "dry ₱270.00" (explicit price, no qty)
      "2.55mm ₱39.00 (15pcs)" (explicit price + qty)
    """
    norm = _normalize_name(line.strip())
    if not norm:
        return None

    # Sandpaper grades: "#60" etc (may appear as "#60" or just "60" in the script).
    if "₱" not in norm:
        if norm.lstrip().startswith("#"):
            return norm, None
        if re.fullmatch(r"\d+(?:\.\d+)?", norm):
            return f"#{norm}", None

    if "₱" not in norm:
        return None

    parts = norm.split("₱", 1)
    vname = parts[0].strip()
    vprice = _extract_first_price(norm)
    if not vname:
        return None
    return vname, vprice


def _extract_variant_qty(line: str) -> float | None:
    # e.g. "... ₱39.00 (15pcs)"
    m = re.search(r"\(([^)]*?)\)", line)
    if not m:
        return None
    inner = m.group(1)
    m2 = re.search(r"([\d,]+(?:\.\d+)?)\s*pcs", inner, flags=re.IGNORECASE)
    if not m2:
        return None
    return _parse_number(m2.group(1))


def _split_blocks(text: str) -> list[list[str]]:
    # Split by blank lines, but merge cases where a header is followed by
    # variant lines after a blank line (your KYK Metal Drill Bit case).
    raw_blocks: list[list[str]] = []
    for raw in re.split(r"\n\s*\n", text):
        raw = raw.strip()
        if not raw:
            continue
        raw_blocks.append([ln.strip() for ln in raw.splitlines() if ln.strip()])

    merged: list[list[str]] = []
    for blk in raw_blocks:
        if not merged:
            merged.append(blk)
            continue

        prev = merged[-1]
        prev_header = prev[0].lower() if prev else ""
        prev_has_variant_lines = any(("₱" in ln) or ln.lstrip().startswith("#") for ln in prev[1:])
        blk_has_price = any(("₱" in ln) or ln.lstrip().startswith("#") for ln in blk)
        blk_has_reorder = any("reorder point" in ln.lower() for ln in blk)

        if (
            "reorder point" in prev_header
            and not prev_has_variant_lines
            and blk_has_price
            and not blk_has_reorder
        ):
            prev.extend(blk)
        else:
            merged.append(blk)

    return merged


def import_seed_bits_disc() -> None:
    inserted = 0
    updated = 0
    skipped = 0
    skipped_reasons: dict[str, int] = {}
    skipped_items: list[tuple[str, str]] = []

    with app.app_context():
        for block in _split_blocks(SEED_TEXT):
            header = block[0]
            name = _normalize_name(header.split("₱", 1)[0])
            reorder_point = _extract_reorder_point(header)
            header_price = _extract_first_price(header)
            header_qty, header_qty_is_each = _extract_qty_and_each(header)

            if not reorder_point and reorder_point != 0:
                skipped += 1
                skipped_reasons["missing_reorder_point"] = skipped_reasons.get("missing_reorder_point", 0) + 1
                skipped_items.append((name, "missing_reorder_point"))
                continue

            # Variant lines can be either:
            # - lines with explicit prices "₱..."
            # - sandpaper grades "#60" etc (no ₱, price inherited)
            variant_lines = []
            for ln in block[1:]:
                stripped = ln.strip()
                if "₱" in ln or ln.lstrip().startswith("#"):
                    variant_lines.append(ln)
                    continue
                # Sandpaper grades may show up as digit-only lines in SEED_TEXT.
                if re.fullmatch(r"\d+(?:\.\d+)?", stripped):
                    variant_lines.append(ln)

            mat = Material.query.filter_by(name=name, category=CATEGORY).first()
            creating = mat is None
            if creating:
                mat = Material(name=name, category=CATEGORY)
                db.session.add(mat)
                # Ensure mat.id is available for MaterialVariant rows.
                db.session.flush()

            mat.reorder_point = float(reorder_point)
            mat.unit = DEFAULT_UNIT

            if variant_lines:
                # Material with variants: quantity is driven by variants.
                mat.quantity = 0.0
                mat.price_per_unit = float(header_price or 0.0)

                # Keep existing variants by name; update, add missing.
                existing = {v.name: v for v in mat.variants}
                for ln in variant_lines:
                    parsed = _parse_variant_line(ln)
                    if not parsed:
                        continue
                    vname, vprice = parsed
                    vqty = _extract_variant_qty(ln)
                    if vqty is None:
                        if header_qty is None:
                            # Can't infer qty for this variant line.
                            skipped += 1
                            skipped_reasons["missing_variant_qty"] = skipped_reasons.get("missing_variant_qty", 0) + 1
                            skipped_items.append((name, "missing_variant_qty"))
                            continue
                        # If header says "... pcs each", use it per variant.
                        # Otherwise, we still use it per variant as a best-effort for seeding.
                        vqty = header_qty

                    v = existing.get(vname)
                    if v is None:
                        effective_price = float(vprice) if vprice is not None else float(header_price or 0.0)
                        v = MaterialVariant(
                            material_id=mat.id,
                            name=vname,
                            quantity=float(vqty),
                            unit=DEFAULT_UNIT,
                            price=effective_price,
                        )
                        db.session.add(v)
                    else:
                        v.quantity = float(vqty)
                        v.unit = DEFAULT_UNIT
                        v.price = float(vprice) if vprice is not None else float(header_price or 0.0)

            else:
                # No variant lines: treat as a single material.
                if header_qty is None:
                    skipped += 1
                    skipped_reasons["missing_quantity"] = skipped_reasons.get("missing_quantity", 0) + 1
                    skipped_items.append((name, "missing_quantity"))
                    continue
                if header_price is None:
                    skipped += 1
                    skipped_reasons["missing_price"] = skipped_reasons.get("missing_price", 0) + 1
                    skipped_items.append((name, "missing_price"))
                    continue
                mat.quantity = float(header_qty)
                mat.price_per_unit = float(header_price)

            if creating:
                inserted += 1
            else:
                updated += 1

        db.session.commit()

    print(f"Bits & Disc import complete.")
    print(f"Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
    for k, v in sorted(skipped_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"- {k}: {v}")
    if skipped_items:
        print("Skipped items:")
        for n, reason in skipped_items:
            print(f"- {n} ({reason})")


if __name__ == "__main__":
    import_seed_bits_disc()

