student: Riza Melih
grupa: 334CD


	main():
		-> initializez priority si interface_vlan_map citind datele din fisierul aferent fiecarui switch din directorul
		configs. 'priority' reprezinta prioritatea switch-ului si 'interface_vlan_map' este un hashMap care mapeaza
		fiecare interfata a switch-ului cu vlan-ul din care face parte. (interfata -> vlan). 'opened_ports' reprezinta
		un hashMap care atribuie fiecarei interfete ale switch-ului starea de deschis (1) sau inchis (0), deci valoarea
		unei interfete in 'opened_ports' este 0 sau 1. 
		
		VLAN-UL 99 L-AM CONSIDERAT TRUNK!
		
		-> 'Table' reprezinta tabela de comutare, initial goala, la fel, reprezentata printr-un hashMap care mapeaza
		mac-ul sursa cu interfata pe care a primit switch-ul pachetul. Tabela va fi folosita daca contine mac-ul destinatie
		si interfata pe care va trebui sa trimitem un pachet, astfel scutindu-ne de flooding.
		
		-> Intr-un alt thread se ruleaza algoritmul STP pentru a dezactiva legaturile ce ar crea bucle.
		Trimt argumentele: sender_mac (mac-ul switch-ului curent care vrea sa trimita un pachet STP), root_bridge_ID 
		(root_bridge-ul considerat de switch-ul curent), own_bridge_ID (practic switch-ul curent, prioritatea lui), 
		interfaces (interfetele detinute de switch-ul curent), si interface_vlan_map (asocierile interfata - vlan de
		pe switch-ul curent).
		
		-> Daca am primit un pachet BDPU apelez functia 'handle_BDPU_received()' ce implementeaza pseudocodul din enunt
		pentru STP.
		
		-> Apoi verific daca 'vlan_id' este -1 caz in care inseamna ca am primit un pachet de la un host pe switch. 
		Verificam daca adresa este unicast (pachetul are un singur destinatar) si apoi verificam daca se afla adresa mac
		destinatie in tabela CAM definita anterior. 
		
		
			Daca da, verific daca portul pe care am primit este deschis (in caz contrar
			ar trebui sa arunc pachetul, adica sa il ignor), si daca este, verific in continuare daca interfata pe
			care ar trebui sa trimit face parte din acelasi vlan cu intrefata pe care am primit, daca intrefata este
			deschisa si daca legatura pe care voi trimite nu este trunk. Daca toate acestea sunt indeplinite, trimit
			pachetul, asa cum l-am primit.
			Alfel, daca interfata pe care trebuie sa trimit este trunk si portul aferent este deschis, voi adauga
			si campul vlan_tag in pachet. (Pentru ca switch-ul care primeste sa stie vlan-ul pachetului).
			
			Daca adresa mac destinatie nu se afla in CAM Table va trebui sa trimit pe toate legaturile pe care le are
			switch-ul, exceptand pe cea pe care a fost primit pachetul.
			Daca interfata pe care a venit pachetul este inchisa, ignor, dau "drop" la pachet.
			Altfel procesul anterior pe care l-am realizat cand tabela CAM contine mac-ul destinatie se repeta si
			se trimite pachetul pe toate interfetele, cu vlan pe legaturi "trunk" si fara pe cele "normale".
			
			 
			Daca pachetul nu este unicast si trebuie trimis prin broadcast, repet procesul anterior din cazul in care
			adresa mac destinatie nu se afla in CAM Table.
			
			
		Daca 'vlan_id' nu este -1 inseamna ca am primit de pe o legatura trunk si aici procesul este asemanator cu cel anterior.
		Daca se afla adresa mac destinatie in CAM Table, verific porturile pe care am primit si trimit sa fie deschise, 
		exista cazul in care trimit pe trunk, cand trimit pachetul original, el venind deja cu vlan_tag, alftel cand trimit pe
		legatura non-trunk ii scot vlan_tag si trimit.
		Daca nu se afla adresa mac destinatie in CAM Table fac flooding.
		
		
	construct_and_send_bdpu():
		
		-> adaug mac-ul destinatie standard '\x01\x80\xC2\x00\x00\x00' apoi concatenez mac-ul switch-ului care trimite,
		dupa care adaug cele root_bridge_ID, sender_path_cost si sender_bridge_ID necesare algoritmului STP. Folosesc astfel,
		protocolul simplificat, rulat de toate switch-urile. Apoi trimit bytii.
		
	send_bdpu_every_sec():
	
		-> functia rulata in parall de thread care initial este apelata de pe toate switch-urile (toate trimit), iar mai apoi doar
		root_bridge-ul va mai trimite la fiecare o secunda detalii pentru rularea STP celorlalte switch-uri.
		
		
	is_unicast_mac():
	
		-> Intoarce adevarat daca adresa este unicat sau fals daca este broadcast.
		
		
	read_config_file():
	
		-> citeste prioritate switch-ului din fisier si construieste hashMap-ul interfata -> vlan pentru interfetele switch-ului.
		Apoi le retunreaza.
