"""Handles sending notifications via the configured notifiers
"""

import json
import structlog
from jinja2 import Template

from emoji import emojize

from notifiers.twilio_client import TwilioNotifier
from notifiers.slack_client import SlackNotifier
from notifiers.discord_client import DiscordNotifier
from notifiers.gmail_client import GmailNotifier
from notifiers.telegram_client import TelegramNotifier
from notifiers.webhook_client import WebhookNotifier
from notifiers.stdout_client import StdoutNotifier


class Notifier():
    """Handles sending notifications via the configured notifiers
    """

    def __init__(self, notifier_config, config):
        """Initializes Notifier class

        Args:
            notifier_config (dict): A dictionary containing configuration for the notifications.
        """

        self.config = config
        self.logger = structlog.get_logger()
        self.notifier_config = notifier_config
        self.last_analysis = dict()

        self.hotImoji = emojize(":hotsprings: ", use_aliases=True)
        self.coldImoji = emojize(":snowman: ", use_aliases=True)
        self.primaryImoji = emojize(":ok_hand: ", use_aliases=True)

        enabled_notifiers = list()
        self.logger = structlog.get_logger()
        self.twilio_configured = self._validate_required_config('twilio', notifier_config)
        if self.twilio_configured:
            self.twilio_client = TwilioNotifier(
                twilio_key=notifier_config['twilio']['required']['key'],
                twilio_secret=notifier_config['twilio']['required']['secret'],
                twilio_sender_number=notifier_config['twilio']['required']['sender_number'],
                twilio_receiver_number=notifier_config['twilio']['required']['receiver_number']
            )
            enabled_notifiers.append('twilio')

        self.discord_configured = self._validate_required_config('discord', notifier_config)
        if self.discord_configured:
            self.discord_client = DiscordNotifier(
                webhook=notifier_config['discord']['required']['webhook'],
                username=notifier_config['discord']['required']['username'],
                avatar=notifier_config['discord']['optional']['avatar']
            )
            enabled_notifiers.append('discord')

        self.slack_configured = self._validate_required_config('slack', notifier_config)
        if self.slack_configured:
            self.slack_client = SlackNotifier(
                slack_webhook=notifier_config['slack']['required']['webhook']
            )
            enabled_notifiers.append('slack')

        self.gmail_configured = self._validate_required_config('gmail', notifier_config)
        if self.gmail_configured:
            self.gmail_client = GmailNotifier(
                username=notifier_config['gmail']['required']['username'],
                password=notifier_config['gmail']['required']['password'],
                destination_addresses=notifier_config['gmail']['required']['destination_emails']
            )
            enabled_notifiers.append('gmail')

        self.telegram_configured = self._validate_required_config('telegram', notifier_config)
        if self.telegram_configured:
            self.telegram_client = TelegramNotifier(
                token=notifier_config['telegram']['required']['token'],
                chat_id=notifier_config['telegram']['required']['chat_id'],
                parse_mode=notifier_config['telegram']['optional']['parse_mode']
            )
            enabled_notifiers.append('telegram')

        self.webhook_configured = self._validate_required_config('webhook', notifier_config)
        if self.webhook_configured:
            self.webhook_client = WebhookNotifier(
                url=notifier_config['webhook']['required']['url'],
                username=notifier_config['webhook']['optional']['username'],
                password=notifier_config['webhook']['optional']['password']
            )
            enabled_notifiers.append('webhook')

        self.stdout_configured = self._validate_required_config('stdout', notifier_config)
        if self.stdout_configured:
            self.stdout_client = StdoutNotifier()
            enabled_notifiers.append('stdout')

        self.logger.info('enabled notifers: %s', enabled_notifiers)

    def notify_all(self, new_analysis):
        """Trigger a notification for all notification options.

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        self.notify_slack(new_analysis)
        self.notify_discord(new_analysis)
        self.notify_twilio(new_analysis)
        self.notify_gmail(new_analysis)
        self.notify_telegram(new_analysis)
        self.notify_webhook(new_analysis)
        self.notify_stdout(new_analysis)

    def notify_all_new(self, new_analysis):
        """Trigger a notification for all notification options.

        Args:
            new_analysis (dict): The new_analysis to send.
            :param config:
        """

        self._indicator_message_templater(
            new_analysis,
            self.notifier_config['slack']['optional']['template']
        )
        print()

    def notify_discord(self, new_analysis):
        """Send a notification via the discord notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.discord_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['discord']['optional']['template']
            )
            if message.strip():
                self.discord_client.notify(message)

    def notify_slack(self, new_analysis):
        """Send a notification via the slack notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.slack_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['slack']['optional']['template']
            )
            if message.strip():
                self.slack_client.notify(message)

    def notify_twilio(self, new_analysis):
        """Send a notification via the twilio notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.twilio_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['twilio']['optional']['template']
            )
            if message.strip():
                self.twilio_client.notify(message)

    def notify_gmail(self, new_analysis):
        """Send a notification via the gmail notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.gmail_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['gmail']['optional']['template']
            )
            if message.strip():
                self.gmail_client.notify(message)

    def notify_telegram(self, new_analysis):
        """Send a notification via the telegram notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.telegram_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['telegram']['optional']['template']
            )
            if message.strip():
                self.telegram_client.notify(message)

    def notify_webhook(self, new_analysis):
        """Send a notification via the webhook notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.webhook_configured:
            for exchange in new_analysis:
                for market in new_analysis[exchange]:
                    for indicator_type in new_analysis[exchange][market]:
                        for indicator in new_analysis[exchange][market][indicator_type]:
                            for index, analysis in enumerate(new_analysis[exchange][market][indicator_type][indicator]):
                                analysis_dict = analysis['result'].to_dict(orient='records')
                                if analysis_dict:
                                    new_analysis[exchange][market][indicator_type][indicator][index] = analysis_dict[-1]
                                else:
                                    new_analysis[exchange][market][indicator_type][indicator][index] = ''

            self.webhook_client.notify(new_analysis)

    def notify_stdout(self, new_analysis):
        """Send a notification via the stdout notifier

        Args:
            new_analysis (dict): The new_analysis to send.
        """

        if self.stdout_configured:
            message = self._indicator_message_templater(
                new_analysis,
                self.notifier_config['stdout']['optional']['template']
            )
            if message.strip():
                self.stdout_client.notify(message)

    def _validate_required_config(self, notifier, notifier_config):
        """Validate the required configuration items are present for a notifier.

        Args:
            notifier (str): The name of the notifier key in default-config.json
            notifier_config (dict): A dictionary containing configuration for the notifications.

        Returns:
            bool: Is the notifier configured?
        """

        notifier_configured = True
        for _, val in notifier_config[notifier]['required'].items():
            if not val:
                notifier_configured = False
        return notifier_configured

    def _indicator_message_templater(self, new_analysis, template):
        """Creates a message from a user defined template

        Args:
            new_analysis (dict): A dictionary of data related to the analysis to send a message about.
            template (str): A Jinja formatted message template.

        Returns:
            str: The templated messages for the notifier.
        """

        if not self.last_analysis:
            self.last_analysis = new_analysis

        customCode = True

        message_template = Template(template)
        new_message = str()
        for exchange in new_analysis:
            for market in new_analysis[exchange]:

                base_currency, quote_currency = market.split('/')

                sendNotification = False
                allIndicatorData = {}
                primaryIndicators = []
                crossedData = {}
                informatntData = {}
                couldCount = 0
                hotCount = 0

                allIndicatorData["name"] = base_currency + quote_currency
                allIndicatorData["exchange"] = exchange
                allIndicatorData["crossed"] = {}
                allIndicatorData["informants"] = {}

                for indicator_type in new_analysis[exchange][market]:

                    print(indicator_type)

                    for indicator in new_analysis[exchange][market][indicator_type]:

                        for index, analysis in enumerate(new_analysis[exchange][market][indicator_type][indicator]):
                            if analysis['result'].shape[0] == 0:
                                continue

                            values = dict()
                            jsonIndicator = {}

                            if indicator_type == 'informants':
                                for signal in analysis['config']['signal']:
                                    latest_result = analysis['result'].iloc[-1]

                                    values[signal] = analysis['result'].iloc[-1][signal]
                                    if isinstance(values[signal], float):
                                        values[signal] = format(values[signal], '.8f')

                                informent_result = {"result": values, "config": analysis['config']}
                                informatntData[indicator] = informent_result
                                continue

                            elif indicator_type == 'indicators':
                                for signal in analysis['config']['signal']:
                                    latest_result = analysis['result'].iloc[-1]

                                    values[signal] = analysis['result'].iloc[-1][signal]
                                    if isinstance(values[signal], float):
                                        values[signal] = format(values[signal], '.8f')

                            elif indicator_type == 'crossovers':
                                latest_result = analysis['result'].iloc[-1]
                                crosedIndicator = True
                                allIndicatorData["crosed"] = crosedIndicator

                                key_signal = '{}_{}'.format(
                                    analysis['config']['key_signal'],
                                    analysis['config']['key_indicator_index']
                                )

                                crossed_signal = '{}_{}'.format(
                                    analysis['config']['crossed_signal'],
                                    analysis['config']['crossed_indicator_index']
                                )

                                values[key_signal] = analysis['result'].iloc[-1][key_signal]
                                if isinstance(values[key_signal], float):
                                    values[key_signal] = format(values[key_signal], '.8f')

                                values[crossed_signal] = analysis['result'].iloc[-1][crossed_signal]
                                if isinstance(values[crossed_signal], float):
                                    values[crossed_signal] = format(values[crossed_signal], '.8f')

                                dataCros = {"name": key_signal[0:-2], "key_value": values[key_signal],
                                            "crossed_value": values[crossed_signal],
                                            "is_hot": True if latest_result['is_hot'] else False,
                                            "is_cold": True if latest_result['is_cold'] else False}
                                dataCros["key_config"] = \
                                    new_analysis[exchange][market]['informants'][dataCros["name"]][0]["config"]
                                dataCros["crossed_config"] = \
                                    new_analysis[exchange][market]['informants'][dataCros["name"]][1]["config"]

                                crossedData[dataCros["name"]] = dataCros
                                continue

                            status = 'neutral'
                            if latest_result['is_hot']:
                                status = 'hot'
                                if indicator != "ichimoku" and indicator_type != "informants" and indicator_type != "crossovers":
                                    hotCount += 1
                            elif latest_result['is_cold']:
                                status = 'cold'
                                if indicator != "ichimoku" and indicator_type != "informants" and indicator_type != "crossovers":
                                    couldCount += 1

                            # Save status of indicator's new analysis
                            new_analysis[exchange][market][indicator_type][indicator][index]['status'] = status

                            if latest_result['is_hot'] or latest_result['is_cold'] or customCode:
                                try:
                                    last_status = \
                                        self.last_analysis[exchange][market][indicator_type][indicator][index]['status']
                                except:
                                    last_status = str()

                                should_alert = True
                                try:
                                    if analysis['config']['alert_frequency'] == 'once':
                                        if last_status == status:
                                            should_alert = False

                                    if not analysis['config']['alert_enabled']:
                                        should_alert = False
                                except Exception as ex:
                                    print(ex)

                                jsonIndicator["values"] = values
                                jsonIndicator["exchange"] = exchange
                                jsonIndicator["market"] = market
                                jsonIndicator["base_currency"] = base_currency
                                jsonIndicator["quote_currency"] = quote_currency
                                jsonIndicator["indicator"] = indicator
                                jsonIndicator["indicator_number"] = index

                                jsonIndicator["config"] = analysis['config']

                                jsonIndicator["status"] = status
                                jsonIndicator["last_status"] = last_status

                                if (latest_result['is_hot'] or latest_result['is_cold']) and should_alert:
                                    sendNotification = True

                                    primaryIndicators.append(indicator)

                                    new_message += message_template.render(
                                        values=values,
                                        exchange=exchange,
                                        market=market,
                                        base_currency=base_currency,
                                        quote_currency=quote_currency,
                                        indicator=indicator,
                                        indicator_number=index,
                                        analysis=analysis,
                                        status=status,
                                        last_status=last_status
                                    )

                                    if len(primaryIndicators) == 0:
                                        jsonIndicator["primary"] = True
                                    else:
                                        jsonIndicator["primary"] = False

                                else:
                                    jsonIndicator["primary"] = False

                                allIndicatorData[indicator] = jsonIndicator
                myset = self.config.settings
                if sendNotification == True and len(primaryIndicators) >= 2 and \
                        (hotCount >= myset["max_hot_notification"] or couldCount >= myset["max_cold_notification"]):
                    allIndicatorData["crossed"] = crossedData
                    allIndicatorData["informants"] = informatntData
                    print("Hot : " + str(hotCount) + "  cold : " + str(couldCount))
                    self.notify_custom_telegram(allIndicatorData)
                    # exit()

        # Merge changes from new analysis into last analysis
        self.last_analysis = {**self.last_analysis, **new_analysis}
        return new_message

    def bollinger_bands_state_calculation(self, upperband, middleband, lowerband, v_close):

        isInTop = v_close > middleband
        isDown = v_close < middleband

        isCold = isHot = False

        if isInTop:
            diff_close = upperband - v_close
            diff_med = v_close - middleband

            isCold = diff_close < diff_med

        elif isDown:
            diff_close = v_close - lowerband
            diff_med = middleband - v_close

            isHot = diff_close < diff_med

        if isCold:
            return "cold"
        elif isHot:
            return "hot"
        else:
            return "neutral"

    def moving_avg_status(self, key_value, crossed_value, is_hot, key_config, crossed_config):

        if is_hot:
            message = str(key_config["period_count"]) + " up " + str(crossed_config["period_count"])
        else:
            message = str(key_config["period_count"]) + " down " + str(crossed_config["period_count"])

        message += self.status_generator(False, "hot" if is_hot else "cold")
        # message += "\n \t" + key_config["candle_period"] + "/" + str(key_config["period_count"]) + " ====> " + str(
        # key_value) message += "\n \t" + crossed_config["candle_period"] + "/" + str(crossed_config["period_count"])
        #  + " ====> " + str(crossed_value)

        return message

    def status_generator(self, primary, state):
        message = str()

        if primary and (state == "cold" or state == "hot"):
            message += self.primaryImoji
        elif state == "cold":
            message += self.coldImoji
        elif state == "hot":
            message += self.hotImoji

        message += "\n"
        return " " + message

    def notify_custom_telegram(self, objectsData):
        """Send a notification via the telegram notifier

        Args:
            objectsData (dict): The new_analysis to send.
        """

        # print(json.dumps(objectsData))

        try:
            message = str()

            # Crypto Name
            message = emojize(":gem:", use_aliases=True) + " #" + objectsData["name"] + "\n"

            # Market Name
            message += self.config.settings["period_data"] + " / " + objectsData["exchange"] + "\n"
            message += "#Price -- " + objectsData["informants"]["ohlcv"]["result"]["close"] + " BTC \n\n"

            # MFI
            mfi = objectsData["mfi"]
            message += "MFI - is " + mfi["status"] + " (" + mfi["values"]["mfi"] + ") "
            message += self.status_generator(mfi["primary"], mfi["status"])

            # RSI
            rsi = objectsData["rsi"]
            message += "RSI - is " + rsi["status"] + " (" + rsi["values"]["rsi"] + ")"
            message += self.status_generator(rsi["primary"], rsi["status"])

            # STOCH_RSI
            stock_rsi = objectsData["stoch_rsi"]
            message += "STOCH_RSI - is " + stock_rsi["status"] + " (" + stock_rsi["values"]["stoch_rsi"] + ")"
            message += self.status_generator(stock_rsi["primary"], stock_rsi["status"])

            # MACD
            macd = objectsData["macd"]
            message += "MACD - is " + macd["status"] + " (" + macd["values"]["macd"] + ")"
            message += self.status_generator(macd["primary"], macd["status"])

            # Bollinder bands
            bb_result = objectsData["informants"]["bollinger_bands"]["result"]
            bollinger_bands_state = self.bollinger_bands_state_calculation(
                float(bb_result["upperband"]),
                float(bb_result["middleband"]),
                float(bb_result["lowerband"]),
                float(objectsData["informants"]["ohlcv"]["result"]["close"])
            )
            message += "Bollinger Bands - is " + bollinger_bands_state
            message += self.status_generator(False, bollinger_bands_state)
            # message += " \t(upperband ===> " + bb_result["upperband"] + ") \n"
            # message += " \t(middleband ===> " + bb_result["middleband"] + ") \n"
            # message += " \t(lowerband ===> " + bb_result["lowerband"] + ")"

            # EMA Crossed
            ema = objectsData["crossed"]["ema"]
            ema_key_config = ema["key_config"]
            ema_crossed_config = ema["crossed_config"]
            mva_stat = self.moving_avg_status(
                ema["key_value"],
                ema["crossed_value"],
                bool(ema["is_hot"]),
                ema_key_config,
                ema_crossed_config
            )
            message += "Moving Average (ema) " + mva_stat

            # ICHIMOKU
            ichimoku = objectsData["ichimoku"]
            message += "Ichimoku Cloud - is " + ichimoku["status"]
            message += self.status_generator(ichimoku["primary"], ichimoku["status"])

            if self.telegram_configured:
                self.telegram_client.notify(message)

            print(message)

        except Exception as ex:
            print(ex)
