from unittest import case
import os
import re
from unittest.mock import patch
import uu
import sys
import cv2
import pytesseract
import json
import PyPDF2
import numpy as np
import shutil
from enum import Enum
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from datetime import date
from pdf2image import convert_from_path

from odtgen import generate_doc

# VARIABELEN
nummerplaat = None



class Car(Enum):
	OWNER = 1
	DRIVER = 2


def pdf_to_image(filename):
	path = f"fines/{filename}.pdf"
	images = convert_from_path(path)

	# 1 en 2 als het van ALD is
	# 0 en 1 als de eerste pagina van de pdf verwijderd wordt (github)
	images[0].save(f'.temp/{filename}_0' +'.jpg', 'JPEG')
	images[1].save(f'.temp/{filename}_1' +'.jpg', 'JPEG')

def extract_data(filename):
	name = f".temp/{filename}_0.jpg"
	file = Image.open(name)
	string = pytesseract.image_to_string(file, lang='eng')

	# Dossiernummer
	dn_regex = '\d{3}\/\d{4}\/\d{5}'
	dn = re.search(dn_regex, string)
	if dn:
		dn = dn.group()


	name = f".temp/{filename}_1.jpg"
	file = Image.open(name)
	string = pytesseract.image_to_string(file, lang='eng')

	# Proces-verbaal nummer: LE.94.LC.416966/2022
	pvn_regex = 'Proces-verbaal nummer: (LE\.94\.LC\.\d+/\d+)'
	pvn = re.search(pvn_regex, string)
	if pvn:
		pvn = pvn.group(1)

	# Wij, NATHALIE BAUDEWIJNS, van
	nvdf_regex = 'Wij, (.+), van'
	nvdf = re.search(nvdf_regex, string)
	if nvdf:
		nvdf = nvdf.group(1)


	# Op 22-02-2022, 14:18 uur.
	du_regex = 'Op (\d+-\d+-\d+), (\d+:\d+) uur.'
	du = re.search(du_regex, string)
	if du:
		datum = du.group(1)
		uur = du.group(2)


	# Kentekenplaat: 2ASD974
	k_regex = 'Kentekenplaat: (\d\w+\d+)'
	k = re.search(k_regex, string)
	if k:
		k = k.group(1)

	# Houder
	houder_regex = 'HOUDER KENTEKENPLAAT\s(.*?\s.*?)\s'
	houder = re.search(houder_regex, string)
	if houder:
		houder = houder.group(1)

	data = {
		'dossiernummer': dn,
		'proces_verbaal_nummer': pvn,
		'naam_politie': nvdf,
		'datum': datum,
		'uur': uur,
		'kenteken': k,
		'houder': houder
	}

	return data



def delete_background(imagename):
	img = cv2.imread(imagename)

	# Grijs
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)[1]
	mask = 255 - mask

	mask = (2*(mask.astype(np.float32))-255.0).clip(0,255).astype(np.uint8)

	result = img.copy()
	result = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
	result[:, :, 3] = mask

	cv2.imwrite(f'{imagename.split(".")[0]}_cbg.png', result)

def fill_in_defense_doc(dossiernummer, nummerplaat, houdernummerplaat, overtredingsdatum):
	img = Image.open('data/clean_verweer.jpg')

	I1 = ImageDraw.Draw(img)
	myFont = ImageFont.truetype('FreeMono.ttf', 50)

	with open('data/data.json', 'r') as f:
		x = f.read()
	data = json.loads(x)

	# Dossiernummer deel 1
	dossiernummer1 = dossiernummer.split('/')[1]
	I1.text((600, 450), dossiernummer1, font=myFont, fill=(0, 0, 0))

	# Dossiernummer deel 2
	dossiernummer2 = dossiernummer.split('/')[2]
	I1.text((750, 450), dossiernummer2, font=myFont, fill=(0, 0, 0))


	# Nummerplaat
	I1.text((515, 525), nummerplaat, font=myFont, fill=(0, 0, 0))

	# Houder van de nummerplaat
	# TODO: HOUDER
	I1.text((515, 550), houdernummerplaat, font=myFont, fill=(0, 0, 0))

	# Datum
	I1.text((280, 700), str(date.today()), font=myFont, fill=(0, 0, 0))

	# Naam en voornaam bestuurder
	I1.text((515, 900), data['bestuurder'], font=myFont, fill=(0, 0, 0))

	# Straat
	I1.text((600, 990), data['adres']['straat'], font=myFont, fill=(0, 0, 0))

	# Nummer
	I1.text((1120, 990), data['adres']['nummer'], font=myFont, fill=(0, 0, 0))

	# Postcode
	I1.text((635, 1050), data['adres']['postcode'], font=myFont, fill=(0, 0, 0))

	# Woonplaats
	I1.text((990, 1050), data['adres']['woonplaats'], font=myFont, fill=(0, 0, 0))

	# Land
	I1.text((600, 1120), data['adres']['land'], font=myFont, fill=(0, 0, 0))

	# Geboortedatum bestuurder
	I1.text((515, 1220), data['geboortedatum'], font=myFont, fill=(0, 0, 0))

	# email bestuurder
	I1.text((515, 1275), data['email'], font=myFont, fill=(0, 0, 0))

	# verweer
	d = overtredingsdatum.replace('-', '')
	# TODO: verander volgorde
	I1.text((180, 1460), "Hierbij verwijs ik naar bijgevoegd bestand", font=myFont, fill=(0, 0, 0))
	I1.text((170, 1510), f"(verweer_{d}.docx) dat u terug kan", font=myFont, fill=(0, 0, 0))
	I1.text((180, 1570), "vinden in deze mail.", font=myFont, fill=(0, 0, 0))

	# Datum
	# TODO: fix datum vorm
	I1.text((280, 1770), str(date.today()), font=myFont, fill=(0, 0, 0))



	#img.save("done_verweer.jpg")
	img.save(f"verweer/verweer_{overtredingsdatum}.png")

def add_signature(frontImage, driver_owner, backImage):
	frontImage = Image.open(frontImage)
	background = Image.open(backImage)
	
	frontImage = frontImage.convert("RGBA")	
	background = background.convert("RGBA")
	
	if driver_owner == Car.OWNER:
		width = (background.width - frontImage.width)-30
		height = ((background.height - frontImage.height) // 3)-60
	elif driver_owner == Car.DRIVER:
		width = (background.width - frontImage.width)-30
		height = (background.height - frontImage.height)-350
	
	background.paste(frontImage, (width, height), frontImage)
	
	background.save(filename1, format="png")



def resize_signature(file, size):
	path = f'data/{file}.png'
	image = Image.open(path)
	reseized_image = image.resize(size)
	reseized_image.save(path)


if __name__ == '__main__':
	#delete_background('data/handtekening_papa.png')
	#delete_background('data/handtekening_arno.png')

	fines = os.listdir('fines')
	for fine in fines:
		fine = fine.split('.')[0]
		print(fine)
		pdf_to_image(filename=fine)
		data = extract_data(filename=fine)

		print(data)

		# TODO: ask if data is correct
		fill_in_defense_doc(dossiernummer=data.get('dossiernummer'), nummerplaat=data.get('kenteken'), houdernummerplaat=str(data.get("houder")).rstrip(), overtredingsdatum=data.get('datum'))
		print(f"verweer/verweer_{data.get('datum')}.png")
		
		#resize_signature('handtekening_papa_cbg', (370,370))
		#add_signature(backImage=f"verweer/verweer_{data.get('datum')}.png", driver_owner=Car.OWNER, frontImage='data/handtekening_papa_cbg.png')
		#add_signature(backImage=f"verweer/verweer_{data.get('datum')}.png", driver_owner=Car.DRIVER, frontImage='data/handtekening_arno_cbg.png')

		if data.get('naam_politie') is None:
			name_police = ''
		else:
			name_police = data.get('naam_politie')

		generate_doc(name_police=name_police, 
					date_received=data.get('datum'), 
					date_of_offense=data.get('datum'), 
					uur=data.get('uur'),
					name="Arno")


