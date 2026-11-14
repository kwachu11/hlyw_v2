# Drużyny do wyboru w turnieju FIFA - ligi i kluby z EA SPORTS FC 26 (stan na premierę, wrzesień 2025).
# Źródło listy: fifauteam.com/fc-26-leagues-clubs-national-teams. Przy nowej części gry wystarczy podmienić dane poniżej.
# Klucz ligi trafia tylko do formularza; w bazie (fifa_participant.club) zapisuje się sama nazwa klubu.

FIFA_LEAGUES = [
    # (klucz, nazwa wyświetlana, kluby)
    ('premier-league', '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', [
        'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton & Hove Albion', 'Burnley', 'Chelsea',
        'Crystal Palace', 'Everton', 'Fulham', 'Leeds United', 'Liverpool', 'Manchester City', 'Manchester United',
        'Newcastle United', 'Nottingham Forest', 'Sunderland', 'Tottenham Hotspur', 'West Ham United',
        'Wolverhampton Wanderers']),
    ('laliga', '🇪🇸 LALIGA EA SPORTS', [
        'Alavés', 'Athletic Club', 'Atlético Madrid', 'Celta Vigo', 'Elche', 'Espanyol', 'FC Barcelona', 'Getafe',
        'Girona', 'Levante', 'Mallorca', 'Osasuna', 'Rayo Vallecano', 'Real Betis', 'Real Madrid', 'Real Oviedo',
        'Real Sociedad', 'Sevilla FC', 'Valencia', 'Villarreal CF']),
    ('bundesliga', '🇩🇪 Bundesliga', [
        '1. FC Heidenheim', '1. FC Köln', 'TSG Hoffenheim', 'Bayer Leverkusen', 'Bayern Munich', 'Borussia Dortmund',
        'Borussia Mönchengladbach', 'Eintracht Frankfurt', 'FC Augsburg', 'FC St. Pauli', 'Hamburger SV', 'Mainz 05',
        'RB Leipzig', 'SC Freiburg', 'Union Berlin', 'VfB Stuttgart', 'VfL Wolfsburg', 'Werder Bremen']),
    # w grze bez licencji: Inter = „Lombardia FC”, Milan = „Milano FC”, Lazio = „Latium”, Atalanta = „Bergamo Calcio”
    ('serie-a', '🇮🇹 Serie A', [
        'AC Milan (Milano FC)', 'AS Roma', 'Atalanta (Bergamo Calcio)', 'Bologna', 'Cagliari', 'Como', 'Cremonese',
        'Fiorentina', 'Genoa', 'Hellas Verona', 'Inter (Lombardia FC)', 'Juventus', 'Lazio (Latium)', 'Lecce',
        'Napoli', 'Parma', 'Pisa', 'Sassuolo', 'Torino', 'Udinese']),
    ('ligue-1', '🇫🇷 Ligue 1 McDonald\'s', [
        'Angers SCO', 'AS Monaco', 'AJ Auxerre', 'FC Lorient', 'FC Nantes', 'FC Metz', 'Le Havre AC', 'LOSC Lille',
        'OGC Nice', 'Olympique de Marseille', 'Olympique Lyonnais', 'Paris FC', 'Paris Saint-Germain', 'RC Lens',
        'RC Strasbourg Alsace', 'Stade Brestois 29', 'Stade Rennais FC', 'Toulouse FC']),
    ('ekstraklasa', '🇵🇱 PKO BP Ekstraklasa', [
        'Arka Gdynia', 'Bruk-Bet Termalica', 'Cracovia', 'GKS Katowice', 'Górnik Zabrze', 'Jagiellonia Białystok',
        'Korona Kielce', 'Lech Poznań', 'Lechia Gdańsk', 'Legia Warszawa', 'Motor Lublin', 'Piast Gliwice',
        'Pogoń Szczecin', 'Radomiak Radom', 'Raków Częstochowa', 'Widzew Łódź', 'Wisła Płock', 'Zagłębie Lubin']),
    ('eredivisie', '🇳🇱 Eredivisie', [
        'Ajax', 'AZ Alkmaar', 'Excelsior', 'FC Utrecht', 'FC Volendam', 'Feyenoord', 'Fortuna Sittard',
        'Go Ahead Eagles', 'FC Groningen', 'Heracles Almelo', 'NAC Breda', 'NEC Nijmegen', 'PEC Zwolle',
        'PSV Eindhoven', 'SC Heerenveen', 'Sparta Rotterdam', 'Telstar', 'FC Twente']),
    ('liga-portugal', '🇵🇹 Liga Portugal', [
        'Alverca', 'Arouca', 'AVS', 'Casa Pia', 'CD Nacional', 'Estoril', 'Estrela Amadora', 'Famalicão', 'FC Porto',
        'Gil Vicente', 'Moreirense', 'Rio Ave', 'Santa Clara', 'SL Benfica', 'Sporting CP', 'SC Braga', 'Tondela',
        'Vitória de Guimarães']),
    ('super-lig', '🇹🇷 Süper Lig', [
        'Alanyaspor', 'Antalyaspor', 'Beşiktaş', 'Eyüpspor', 'Fatih Karagümrük', 'Fenerbahçe', 'Galatasaray',
        'Gaziantep FK', 'Gençlerbirliği', 'Göztepe', 'İstanbul Başakşehir', 'Kasımpaşa', 'Kayserispor', 'Kocaelispor',
        'Konyaspor', 'Rizespor', 'Samsunspor', 'Trabzonspor']),
    ('saudi', '🇸🇦 ROSHN Saudi League', [
        'Al Ahli', 'Al Fateh', 'Al Fayha', 'Al Hazem', 'Al Hilal', 'Al Ittihad', 'Al Khaleej', 'Al Kholood',
        'Al Najma', 'Al Nassr', 'Al Okhdood', 'Al Qadsiah', 'Al Riyadh', 'Al Shabab', 'Al Taawoun', 'Damac',
        'Al Ettifaq', 'Neom']),
    ('scotland', '🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scottish Premiership', [
        'Aberdeen', 'Celtic', 'Dundee', 'Dundee United', 'Falkirk', 'Heart of Midlothian', 'Hibernian', 'Kilmarnock',
        'Livingston', 'Motherwell', 'Rangers', 'St Mirren']),
    ('belgium', '🇧🇪 Jupiler Pro League', [
        'Cercle Brugge', 'Charleroi', 'Club Brugge', 'Dender EH', 'KRC Genk', 'KAA Gent', 'La Louvière', 'OH Leuven',
        'KV Mechelen', 'Royal Antwerp', 'RSC Anderlecht', 'Sint-Truiden', 'Standard Liège', 'Union SG', 'Westerlo',
        'Zulte Waregem']),
    ('mls', '🇺🇸 MLS', [
        'Atlanta United', 'Austin FC', 'CF Montréal', 'Charlotte FC', 'Chicago Fire', 'Colorado Rapids',
        'Columbus Crew', 'D.C. United', 'FC Cincinnati', 'FC Dallas', 'Houston Dynamo', 'Inter Miami CF', 'LA Galaxy',
        'Los Angeles FC', 'Minnesota United', 'Nashville SC', 'New England Revolution', 'New York City FC',
        'New York Red Bulls', 'Orlando City', 'Philadelphia Union', 'Portland Timbers', 'Real Salt Lake',
        'San Diego FC', 'San Jose Earthquakes', 'Seattle Sounders', 'Sporting Kansas City', 'St. Louis City',
        'Toronto FC', 'Vancouver Whitecaps']),
    ('liga-mx', '🇲🇽 Liga MX', [
        'Club América', 'Atlas', 'Atlético San Luis', 'Cruz Azul', 'Guadalajara', 'FC Juárez', 'León', 'Mazatlán',
        'Monterrey', 'Necaxa', 'Pachuca', 'Puebla', 'Querétaro', 'Santos Laguna', 'Tijuana', 'Toluca', 'Tigres UANL',
        'Pumas UNAM']),
    ('argentina', '🇦🇷 Liga Profesional (Argentyna)', [
        'Aldosivi', 'Argentinos Juniors', 'Atlético Tucumán', 'Banfield', 'Barracas Central', 'Belgrano',
        'Boca Juniors', 'Central Córdoba', 'Defensa y Justicia', 'Deportivo Riestra', 'Estudiantes', 'Gimnasia',
        'Godoy Cruz', 'Huracán', 'Independiente', 'Independiente Rivadavia', 'Instituto', 'Lanús', "Newell's Old Boys",
        'Platense', 'Racing Club', 'River Plate', 'Rosario Central', 'San Lorenzo', 'San Martín', 'Sarmiento',
        'Talleres', 'Tigre', 'Unión', 'Vélez Sarsfield']),
    ('austria', '🇦🇹 Admiral Bundesliga (Austria)', [
        'Blau-Weiß Linz', 'Red Bull Salzburg', 'Austria Wien', 'Grazer AK', 'LASK', 'SCR Altach', 'Rapid Wien',
        'Sturm Graz', 'SV Ried', 'TSV Hartberg', 'Wolfsberger AC', 'WSG Tirol']),
    ('switzerland', '🇨🇭 Super League (Szwajcaria)', [
        'BSC Young Boys', 'FC Basel', 'Lausanne-Sport', 'FC Lugano', 'FC Luzern', 'FC Sion', 'FC St. Gallen',
        'FC Zürich', 'Grasshopper', 'Servette', 'FC Thun', 'FC Winterthur']),
    ('denmark', '🇩🇰 Superliga (Dania)', [
        'AGF Aarhus', 'Brøndby IF', 'FC København', 'FC Midtjylland', 'FC Nordsjælland', 'FC Fredericia', 'OB Odense',
        'Randers FC', 'Silkeborg IF', 'SønderjyskE', 'Vejle BK', 'Viborg FF']),
    ('norway', '🇳🇴 Eliteserien (Norwegia)', [
        'Bodø/Glimt', 'Bryne', 'Fredrikstad', 'HamKam', 'Haugesund', 'KFUM Oslo', 'Kristiansund', 'Molde',
        'Rosenborg', 'Sandefjord', 'Sarpsborg 08', 'SK Brann', 'Strømsgodset', 'Tromsø', 'Vålerenga', 'Viking']),
    ('sweden', '🇸🇪 Allsvenskan (Szwecja)', [
        'AIK', 'BK Häcken', 'Degerfors IF', 'Djurgårdens IF', 'GAIS', 'Halmstads BK', 'Hammarby IF',
        'IF Brommapojkarna', 'IF Elfsborg', 'IFK Göteborg', 'IFK Norrköping', 'IFK Värnamo', 'IK Sirius', 'Malmö FF',
        'Mjällby AIF', 'Östers IF']),
    ('championship', '🏴󠁧󠁢󠁥󠁮󠁧󠁿 EFL Championship', [
        'Birmingham City', 'Blackburn Rovers', 'Bristol City', 'Charlton Athletic', 'Coventry City', 'Derby County',
        'Hull City', 'Ipswich Town', 'Leicester City', 'Middlesbrough', 'Millwall', 'Norwich City', 'Oxford United',
        'Portsmouth', 'Preston North End', 'Queens Park Rangers', 'Sheffield United', 'Sheffield Wednesday',
        'Southampton', 'Stoke City', 'Swansea City', 'Watford', 'West Bromwich Albion', 'Wrexham']),
    ('2-bundesliga', '🇩🇪 2. Bundesliga', [
        '1. FC Kaiserslautern', '1. FC Magdeburg', '1. FC Nürnberg', 'Arminia Bielefeld', 'Darmstadt 98',
        'Dynamo Dresden', 'Eintracht Braunschweig', 'Fortuna Düsseldorf', 'Greuther Fürth', 'Hannover 96',
        'Hertha BSC', 'Holstein Kiel', 'Karlsruher SC', 'Preußen Münster', 'SC Paderborn', 'Schalke 04',
        'SV Elversberg', 'VfL Bochum']),
    ('serie-b', '🇮🇹 Serie BKT', [
        'Avellino', 'Bari', 'Carrarese', 'Catanzaro', 'Cesena', 'Empoli', 'Frosinone', 'Juve Stabia', 'Mantova',
        'Modena', 'Monza (Brianza Calcio)', 'Padova', 'Palermo', 'Pescara', 'Reggiana', 'Sampdoria', 'Spezia',
        'Südtirol', 'Venezia', 'Virtus Entella']),
    ('laliga-2', '🇪🇸 LALIGA HYPERMOTION', [
        'Albacete', 'Almería', 'FC Andorra', 'Burgos', 'Cádiz', 'Castellón', 'Ceuta', 'Córdoba CF',
        'Cultural Leonesa', 'Deportivo La Coruña', 'SD Eibar', 'Granada', 'Huesca', 'Las Palmas', 'Leganés', 'Málaga',
        'Mirandés', 'Racing Santander', 'Real Sociedad B', 'Sporting Gijón', 'Real Valladolid', 'Real Zaragoza']),
    ('ligue-2', '🇫🇷 Ligue 2', [
        'Amiens SC', 'AS Saint-Étienne', 'Boulogne', 'Clermont Foot', 'Dunkerque', 'EA Guingamp', 'FC Annecy',
        'Grenoble Foot 38', 'Stade Lavallois', 'Le Mans FC', 'Montpellier HSC', 'AS Nancy Lorraine', 'Pau FC',
        'Red Star FC', 'Stade de Reims', 'Rodez Aveyron', 'SC Bastia', 'ES Troyes AC']),
    ('reszta', '🌍 Reszta świata', [
        'AEK Ateny', 'Al Ain', 'APOEL', 'Dynamo Kijów', 'Dinamo Zagrzeb', 'Ferencváros', 'Hajduk Split',
        'HJK Helsinki', 'Olympiakos', 'Panathinaikos', 'PAOK', 'Qarabağ', 'Szachtar Donieck', 'Slavia Praga',
        'Sparta Praga', 'Viktoria Pilzno']),
    ('reprezentacje', '🌐 Reprezentacje', [
        'Anglia', 'Argentyna', 'Chorwacja', 'Czechy', 'Dania', 'Finlandia', 'Francja', 'Ghana', 'Hiszpania',
        'Holandia', 'Irlandia', 'Irlandia Północna', 'Islandia', 'Katar', 'Maroko', 'Meksyk', 'Niemcy', 'Norwegia',
        'Nowa Zelandia', 'Polska', 'Portugalia', 'Rumunia', 'Szkocja', 'Szwecja', 'Ukraina', 'USA', 'Walia', 'Węgry',
        'Włochy']),
]

FIFA_OTHER = 'inny'          # w formularzu: „Inna drużyna” - nazwa wpisana ręcznie
FIFA_CLUB_MAX = 60


def club_league(club):
    """Nazwa ligi, w której jest klub (do wyświetlania), albo None dla nazwy spoza listy."""
    key = (club or '').strip().lower()
    for _, label, clubs in FIFA_LEAGUES:
        if any(c.lower() == key for c in clubs):
            return label
    return None


def resolve_club(league_key, club, custom=''):
    """Klub z formularza -> poprawna nazwa z listy (albo wpisana ręcznie przy „Inna drużyna”); None, gdy się nie zgadza."""
    if league_key == FIFA_OTHER:
        name = ' '.join((custom or '').split())[:FIFA_CLUB_MAX]
        return name or None
    for key, _, clubs in FIFA_LEAGUES:
        if key == league_key:
            return next((c for c in clubs if c == club), None)
    return None
