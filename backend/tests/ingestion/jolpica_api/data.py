"""Small hand-built Jolpica responses shaped like the real API (all numbers are strings)."""


def circuit(
    circuit_id="bahrain", name="Bahrain International Circuit", locality="Sakhir", country="Bahrain"
):
    return {
        "circuitId": circuit_id,
        "circuitName": name,
        "Location": {"lat": "26.0325", "long": "50.5106", "locality": locality, "country": country},
    }


def race(number, name, circuit_data, date, time="15:00:00Z", **sessions):
    body = {
        "season": "2024",
        "round": str(number),
        "raceName": name,
        "date": date,
        "time": time,
        "Circuit": circuit_data,
    }
    body.update(sessions)
    return body


def schedule(*races):
    return {"RaceTable": {"season": "2024", "Races": list(races)}}


BAHRAIN = race(
    1,
    "Bahrain Grand Prix",
    circuit(),
    "2024-03-02",
    FirstPractice={"date": "2024-02-29", "time": "11:30:00Z"},
    SecondPractice={"date": "2024-02-29", "time": "15:00:00Z"},
    ThirdPractice={"date": "2024-03-01", "time": "12:30:00Z"},
    Qualifying={"date": "2024-03-01", "time": "16:00:00Z"},
)
CHINA = race(
    5,
    "Chinese Grand Prix",
    circuit("shanghai", "Shanghai International Circuit", "Shanghai", "China"),
    "2024-04-21",
    time="07:00:00Z",
    FirstPractice={"date": "2024-04-19", "time": "03:30:00Z"},
    SprintQualifying={"date": "2024-04-19", "time": "07:30:00Z"},
    Sprint={"date": "2024-04-20", "time": "03:00:00Z"},
    Qualifying={"date": "2024-04-20", "time": "07:00:00Z"},
)

VER = {
    "driverId": "max_verstappen",
    "permanentNumber": "1",
    "code": "VER",
    "givenName": "Max",
    "familyName": "Verstappen",
    "dateOfBirth": "1997-09-30",
    "nationality": "Dutch",
}
PER = {
    "driverId": "perez",
    "permanentNumber": "11",
    "code": "PER",
    "givenName": "Sergio",
    "familyName": "Pérez",
    "dateOfBirth": "1990-01-26",
    "nationality": "Mexican",
}
SAI = {
    "driverId": "sainz",
    "permanentNumber": "55",
    "code": "SAI",
    "givenName": "Carlos",
    "familyName": "Sainz",
    "dateOfBirth": "1994-09-01",
    "nationality": "Spanish",
}
RED_BULL = {"constructorId": "red_bull", "name": "Red Bull", "nationality": "Austrian"}
FERRARI = {"constructorId": "ferrari", "name": "Ferrari", "nationality": "Italian"}


def result_row(
    position,
    text,
    driver,
    constructor,
    points,
    status="Finished",
    grid="1",
    millis="5504742",
    rank=None,
):
    row = {
        "number": "1",
        "position": str(position),
        "positionText": text,
        "points": str(points),
        "Driver": driver,
        "Constructor": constructor,
        "grid": grid,
        "laps": "57",
        "status": status,
    }
    if millis:
        row["Time"] = {"millis": millis, "time": "1:31:44.742"}
    if rank:
        row["FastestLap"] = {"rank": str(rank), "lap": "39", "Time": {"time": "1:32.608"}}
    return row


def results(*rows, key="Results", number=1, name="Bahrain Grand Prix"):
    return {
        "RaceTable": {
            "season": "2024",
            "round": str(number),
            "Races": [{"season": "2024", "round": str(number), "raceName": name, key: list(rows)}],
        }
    }


def qualifying(*rows):
    return {
        "RaceTable": {
            "Races": [{"season": "2024", "round": "1", "QualifyingResults": list(rows)}],
        }
    }


def quali_row(position, driver, constructor, q1, q2=None, q3=None):
    row = {
        "number": "1",
        "position": str(position),
        "Driver": driver,
        "Constructor": constructor,
        "Q1": q1,
    }
    if q2:
        row["Q2"] = q2
    if q3:
        row["Q3"] = q3
    return row


def driver_standings(*items, number=1):
    return {
        "StandingsTable": {
            "StandingsLists": [
                {
                    "season": "2024",
                    "round": str(number),
                    "DriverStandings": [
                        {
                            "position": str(pos),
                            "positionText": str(pos),
                            "points": str(points),
                            "wins": str(wins),
                            "Driver": driver,
                            "Constructors": [],
                        }
                        for pos, points, wins, driver in items
                    ],
                }
            ]
        }
    }


def constructor_standings(*items, number=1):
    return {
        "StandingsTable": {
            "StandingsLists": [
                {
                    "season": "2024",
                    "round": str(number),
                    "ConstructorStandings": [
                        {
                            "position": str(pos),
                            "positionText": str(pos),
                            "points": str(points),
                            "wins": str(wins),
                            "Constructor": constructor,
                        }
                        for pos, points, wins, constructor in items
                    ],
                }
            ]
        }
    }


class FakeClient:
    """Returns canned MRData per endpoint and counts calls. Unknown endpoints fail loudly."""

    def __init__(self, **responses):
        self.responses = responses
        self.calls = []

    def _get(self, name, *args):
        self.calls.append((name, *args))
        if name not in self.responses:
            raise AssertionError(f"unexpected call {name}{args}")
        return self.responses[name]

    def schedule(self, year):
        return self._get("schedule", year)

    def results(self, year, number):
        return self._get("results", year, number)

    def sprint(self, year, number):
        return self._get("sprint", year, number)

    def qualifying(self, year, number):
        return self._get("qualifying", year, number)

    def driver_standings(self, year, number):
        return self._get("driver_standings", year, number)

    def constructor_standings(self, year, number):
        return self._get("constructor_standings", year, number)
