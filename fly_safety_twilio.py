from flask import Flask, request, render_template, url_for
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from bs4 import BeautifulSoup
import requests
import emoji
import os

# DO NOT USE FOR FLIGHT
# FOR SIMULATOR AND EDUCATIONAL PURPOSES ONLY


class METARData:

    def __init__(self, page_data: str):
        soup = BeautifulSoup(page_data, features='lxml')
        self.raw_text = soup.find('raw_text').string
        self.dew_point_c = float(soup.find('dewpoint_c').string)
        self.wind_dir_degrees = int(soup.find('wind_dir_degrees').string)
        self.wind_speed_kt = int(soup.find('wind_speed_kt').string)
        self.visibility_mi = int(soup.find('visibility_statute_mi').string)
        self.pressure_mb = int(soup.find('sea_level_pressure_mb').string)
        self.temp_c = float(soup.find('temp_c').string)
        self.elevation = float(soup.find('elevation_m').string)

    @property
    def temp_f(self) -> float:
        return (self.temp_c * 1.8) + 32

    @property
    def isa_temp(self):
        return 2 * self.elevation - 15

    @property
    def density_altitude(self) -> float:
        da = 3.28084 * (self.pressure_mb + (120 * (self.temp_c - self.isa_temp)))
        return int(round(da))

    @property
    def relative_humidity(self) -> float:
        return round(100 * (self.dew_point_c / self.temp_c))

    @property
    def score_temp_vs_rh(self) -> int:
        if self.temp_f < self.relative_humidity:
            return 7
        if self.temp_f < self.relative_humidity + 5:
            return 5
        return 2

    @property
    def score_wind_speed(self) -> int:
        if self.wind_speed_kt < 6:
            return self.wind_speed_kt
        return self.wind_speed_kt + (self.wind_speed_kt - 6) * 2

    @property
    def score_visibility(self) -> int:
        values = ((1, 5), (2, 3), (3, 1))
        for vis, score in values:
            if self.visibility_mi < vis:
                return score
        return 0

    @property
    def score_pressure(self) -> int:
        if self.pressure_mb <= 1015:
            return 3
        return 1

    @property
    def score(self) -> int:
        s = self.score_temp_vs_rh
        s += self.score_wind_speed
        s += self.score_visibility
        s += self.score_pressure
        return s

    @property
    def emoji(self):
        sc = self.score
        if sc <= 12:
            return emoji.emojize(':green_heart:')
        elif 13 <= sc <= 17:
            return emoji.emojize(':yellow_heart:')
        elif 18 <= sc:
            return emoji.emojize(':red_heart:')


def data_gather(station_code: str) -> METARData:
    data = {'dataSource': 'metars',
            'requestType': 'retrieve',
            'format': 'xml',
            'stationString': station_code,
            'hoursBeforeNow': 1}
    url = 'https://www.aviationweather.gov/adds/dataserver_current/httpparam'
    data = requests.get(url, params=data)
    # TODO: Test num_results="0" needs good error message
    return METARData(data.text)

"""
stationString empty
---
<response xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XML-Schema-instance" version="1.2" xsi:noNamespaceSchemaLocation="http://aviationweather.gov/adds/schema/metar1_2.xsd">
<request_index>17957396</request_index>
<data_source name="metars"/>
<request type="retrieve"/>
<errors>
<error>
Invalid station string: station string cannot be empty
</error>
</errors>
<warnings/>
<time_taken_ms>0</time_taken_ms>
</response>
"""

"""
Non-unique station string

<response xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XML-Schema-instance" version="1.2" xsi:noNamespaceSchemaLocation="http://aviationweather.gov/adds/schema/metar1_2.xsd">
<request_index>30017987</request_index>
<data_source name="metars"/>
<request type="retrieve"/>
<errors/>
<warnings/>
<time_taken_ms>20</time_taken_ms>
<data num_results="2">
<METAR>
<raw_text>
AGGH 031500Z 18003KT 9999 FEW015 SCT025 24/24 Q1010
</raw_text>
<station_id>AGGH</station_id>
<observation_time>2019-08-03T15:00:00Z</observation_time>
<latitude>-9.42</latitude>
<longitude>160.05</longitude>
<temp_c>24.0</temp_c>
<dewpoint_c>24.0</dewpoint_c>
<wind_dir_degrees>180</wind_dir_degrees>
<wind_speed_kt>3</wind_speed_kt>
<visibility_statute_mi>6.21</visibility_statute_mi>
<altim_in_hg>29.822834</altim_in_hg>
<sky_condition sky_cover="FEW" cloud_base_ft_agl="1500"/>
<sky_condition sky_cover="SCT" cloud_base_ft_agl="2500"/>
<flight_category>VFR</flight_category>
<metar_type>METAR</metar_type>
<elevation_m>9.0</elevation_m>
</METAR>
<METAR>
<raw_text>AYPY 031500Z 15005KT 9999 FEW050 24/22 Q1011</raw_text>
<station_id>AYPY</station_id>
<observation_time>2019-08-03T15:00:00Z</observation_time>
<latitude>-9.42</latitude>
<longitude>147.22</longitude>
<temp_c>24.0</temp_c>
<dewpoint_c>22.0</dewpoint_c>
<wind_dir_degrees>150</wind_dir_degrees>
<wind_speed_kt>5</wind_speed_kt>
<visibility_statute_mi>6.21</visibility_statute_mi>
<altim_in_hg>29.852362</altim_in_hg>
<sky_condition sky_cover="FEW" cloud_base_ft_agl="5000"/>
<flight_category>VFR</flight_category>
<metar_type>METAR</metar_type>
<elevation_m>47.0</elevation_m>
</METAR>
</data>
</response>
"""

# app = Flask(__name__)
#
# @app.route("/sms", methods=['GET', 'POST'])
# def twilio_receive():
#     """Respond to incoming messages with a friendly SMS."""
#
#     # get the message the user sent
#     station_name = request.values.get('Body', None)
#
#     # Start our response
#     resp = MessagingResponse()
#
#     metar = data_gather(station_name)
#
#     # Add a message - can send variables of strings.
#     resp.message(f'{metar.emoji} {metar.score}')
#
#     return str(resp)


if __name__ == '__main__':
    metar = data_gather('kind')
    print(metar)
    # app.run(debug=True)
