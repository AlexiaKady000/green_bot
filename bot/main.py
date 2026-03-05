from os import environ
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from classes.utilities import *
from classes.database import *  # Connects to the database here
from res.strings import strings
import json
import functools
print = functools.partial(print, flush=True)


from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, Bot)
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, Filters)
from telegram.error import BadRequest

def new_column(*args):
    '''a, b, c -> [[a], [b], [c]]'''
    return [[arg] for arg in args]

def get_upcoming_collection_action_date():
    '''Opens updating_info.json, gets upcoming_collection_action_date'''
    with open('updating_info.json') as updating_info_file:
        updating_info = json.load(updating_info_file)
    return updating_info["upcoming_collection_action_date"]

# Strings are in "strings.xml", file "res"
keyboard_main = new_column(
    strings["btn_report_bin_overflow"],
    strings["btn_upcoming_collection_action"],
    strings["btn_collection_point_map"],
    strings["btn_separate_collection_rules"],
    strings["btn_for_volunteers"],
    strings["btn_destiny_of_collected_waste"],
    strings["btn_newsletter"]
)

keyboard_subscription = new_column(
    strings["btn_subscribe"],
    strings["btn_unsubscribe"],
    strings["btn_back_to_main"]
)

keyboard_yes_no = new_column(
    strings["btn_yes"],
    strings["btn_no"],
    strings["btn_back_to_main"]
)

keyboard_volunteer_choise = new_column(
    strings["btn_volunteer_subsribe"],
    strings["btn_volunteer_unsubsribe"],
    strings["btn_i_took_out_waste"],
    strings["btn_back_to_main"]
)

keyboard_volunteer_back = new_column(
    strings["btn_back_to_main"]
)

# These go to the database
keyboard_volunteer_where = make_volunteer_location_keyboard()
keyboard_volunteer_what = make_volunteer_fractions_keyboard()
keyboard_map_what = make_map_core_fractions_keyboard()
keyboard_map_what_other = make_map_other_fractions_keyboard()

fractions_keys_list = ['pet_plastic', 'waste_paper', 'glass']

fractions_keys_list_other = ['batteries', 'plastic_lids',
                             'blisters', 'toothbrushes']

keyboard_rules_what = (
    [[strings[key]] for key in fractions_keys_list] +
    [[strings["btn_other_fractions"]], [strings["btn_back_to_main"]]])

keyboard_rules_what_other = (
    [[strings[key]] for key in fractions_keys_list_other] +
    [[strings["btn_other_fractions"]], [strings["btn_back_to_main"]]])

fraction_rules = {strings[key]: strings[key + "_rules"]
    for key in fractions_keys_list + fractions_keys_list_other}


def send_location(chat_id, station_id):
    '''Goes to DB, sends a geotag about station (station_id) to chat_id'''
    bot = Bot(token=environ.get('TG_TOKEN'))
    latitude, longitude = get_coords_by_map_station_id(station_id)
    bot.sendMessage(chat_id=chat_id, text=get_station_msg(station_id),
                    parse_mode='Markdown')
    bot.sendLocation(chat_id=chat_id, latitude=latitude, longitude=longitude)


@not_registered  # "if not registered"
def start(update: Update, context: CallbackContext):
    first_name_for_md = plain_text_to_md(update.effective_user.first_name)

    update.message.reply_text(
        strings["msg_greeting_on_start"]
        .format(first_name_for_md),
        reply_markup=ReplyKeyboardMarkup(keyboard_main),
        parse_mode='Markdown')
    insert_new_user(update)


@authorized  # If 'authorized' in user
def am_i_admin(update: Update, context: CallbackContext):
    update.message.reply_text("Yes")


@authorized
def annonce(update: Update, context: CallbackContext):
    change_user_state(update.message.chat.id, 'annonce')
    update.message.reply_text(strings["msg_write_a_message_to_send_out"],
        reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_back))


def message_triger(update: Update, context: CallbackContext):
    state = user_state(update.message.chat.id)
    if state['success']:
        state = state['data']
        if update.message.text == strings["btn_back_to_main"]:
            change_user_state(update.message.chat.id, 'main')
            update.message.reply_text(strings["msg_main_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
        elif state == 'main':
            if update.message.text == strings["btn_collection_point_map"]:
                change_user_state(update.message.chat.id, "map-choise")
                new_usage(update.message.chat.id)
                update.message.reply_text(strings["msg_collection_point_map"], reply_markup=ReplyKeyboardMarkup(keyboard_map_what))

            elif update.message.text == strings["btn_separate_collection_rules"]:
                change_user_state(update.message.chat.id, "rules-choise")
                new_usage(update.message.chat.id)
                update.message.reply_text(strings["msg_separate_collection_rules"], reply_markup=ReplyKeyboardMarkup(keyboard_rules_what))

            elif update.message.text == strings["btn_destiny_of_collected_waste"]:
                new_usage(update.message.chat.id)
                update.message.reply_text(strings["msg_destiny_of_collected_waste"], reply_markup=ReplyKeyboardMarkup(keyboard_main),
                parse_mode='Markdown')

            elif update.message.text == strings["btn_upcoming_collection_action"]:
                new_usage(update.message.chat.id)
                upcoming_action_date = get_upcoming_collection_action_date()
                if upcoming_action_date:
                    reply = strings["msg_upcoming_collection_action"].format(upcoming_action_date)
                else:
                    reply = strings["msg_upcoming_collection_action_no_info"]
                update.message.reply_text(reply, reply_markup=ReplyKeyboardMarkup(keyboard_main))

            elif update.message.text == strings["btn_for_volunteers"]:
                change_user_state(update.message.chat.id, 'volunteer-choise')
                update.message.reply_text(strings["msg_volunteers_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_choise))

            elif update.message.text == strings["btn_report_bin_overflow"]:
                change_user_state(update.message.chat.id, 'overflow-where')
                update.message.reply_text(strings["msg_where_overflow"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

            elif update.message.text == strings["btn_newsletter"]:
                change_user_state(update.message.chat.id, 'subscription')
                update.message.reply_text(strings["msg_newsletter_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_subscription))
            else:
                new_usage(update.message.chat.id)
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_main))

        elif state == 'volunteer-choise':
            if [update.message.text] in keyboard_volunteer_choise:
                if update.message.text == strings["btn_i_took_out_waste"]:
                    change_user_state(update.message.chat.id, 'volunteer-where')
                    update.message.reply_text(strings["msg_where_took_out"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

                elif update.message.text == strings["btn_volunteer_subsribe"]:
                    change_user_state(update.message.chat.id, 'volunteer-subscription-where')
                    new_usage(update.message.chat.id)
                    update.message.reply_text(strings["msg_where_subscribe"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

                elif update.message.text == strings["btn_volunteer_unsubsribe"]:
                    data = get_users_subscriptions(update.message.chat.id)
                    key = ([
                        [
                            InlineKeyboardButton(i['where']+':'+i['what'], callback_data="delSub_"+str(i['_id'])),
                        ]
                        for i in data])
                    if len(key) == 0:
                        update.message.reply_text(strings["msg_no_subscriptions"], reply_markup=InlineKeyboardMarkup(key))
                    else:
                        update.message.reply_text(strings["msg_choose_to_unsubscribe"], reply_markup=InlineKeyboardMarkup(key))

            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

        elif state == 'map-choise':
            if update.message.text == strings["btn_other_fractions"]:
                change_user_state(update.message.chat.id, 'map-choise-other')
                update.message.reply_text(update.message.text, reply_markup=ReplyKeyboardMarkup(keyboard_map_what_other))
            elif [update.message.text] in keyboard_map_what:
                list_of_locations = get_map_stations_for_fration(update.message.text)
                key = ([
                    [InlineKeyboardButton(get_map_inline(i), callback_data="getStation_"+str(i['_id']))]
                for i in list_of_locations])
                if len(key) == 1:
                    send_location(update.message.chat.id, get_single_map_stations_for_fration(update.message.text))
                elif len(key) > 1:
                    update.message.reply_text(strings["msg_several_collection_points"], reply_markup=InlineKeyboardMarkup(key))
                else:
                    update.message.reply_text(strings["msg_no_collection_points"], reply_markup=InlineKeyboardMarkup(key))

            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_map_what))
        elif state == 'map-choise-other':
            if update.message.text == strings["btn_other_fractions"]:
                change_user_state(update.message.chat.id, 'map-choise')
                update.message.reply_text(update.message.text, reply_markup=ReplyKeyboardMarkup(keyboard_map_what))
            elif [update.message.text] in keyboard_map_what_other:
                list_of_locations = get_map_stations_for_fration(update.message.text)
                key = ([
                    [InlineKeyboardButton(get_map_inline(i), callback_data="getStation_"+str(i['_id']))]
                for i in list_of_locations])
                if len(key) == 1:
                    send_location(update.message.chat.id, get_single_map_stations_for_fration(update.message.text))
                elif len(key) > 1:
                    update.message.reply_text(strings["msg_several_collection_points"], reply_markup=InlineKeyboardMarkup(key))
                else:
                    update.message.reply_text(strings["msg_no_collection_points"], reply_markup=InlineKeyboardMarkup(key))

            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_map_what_other))

        elif state == 'rules-choise':
            if update.message.text == strings["btn_other_fractions"]:
                change_user_state(update.message.chat.id, 'rules-choise-other')
                update.message.reply_text(update.message.text, reply_markup=ReplyKeyboardMarkup(keyboard_rules_what_other))
            elif [update.message.text] in keyboard_rules_what:
                update.message.reply_text(fraction_rules[update.message.text], reply_markup=ReplyKeyboardMarkup(keyboard_rules_what),
                    parse_mode='Markdown')
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_rules_what))
        elif state == 'rules-choise-other':
            if update.message.text == strings["btn_other_fractions"]:
                change_user_state(update.message.chat.id, 'rules-choise')
                update.message.reply_text(update.message.text, reply_markup=ReplyKeyboardMarkup(keyboard_rules_what))
            elif [update.message.text] in keyboard_rules_what_other:
                update.message.reply_text(fraction_rules[update.message.text], reply_markup=ReplyKeyboardMarkup(keyboard_rules_what_other),
                    parse_mode='Markdown')
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_rules_what_other))

        elif state == 'volunteer-subscription-where':
            if update.message.text in keyboard_volunteer_what:
                change_user_state(update.message.chat.id, 'volunteer-subscription-what')
                save_data(update.message.chat.id, 'where-subscription', update.message.text)
                update.message.reply_text(strings["msg_what_taking_out"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_what[update.message.text]))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

        elif state == 'volunteer-subscription-what':
            if any([update.message.text] in keyboard_volunteer_what[i] for i in keyboard_volunteer_what):
                change_user_state(update.message.chat.id, 'main')
                save_data(update.message.chat.id, 'what-subscription', update.message.text)
                add_subscription(update.message.chat.id)
                update.message.reply_text(strings["msg_subscribed"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"])

        elif state == 'volunteer-where':
            if update.message.text in keyboard_volunteer_what:
                change_user_state(update.message.chat.id, 'volunteer-what')
                save_data(update.message.chat.id, 'where', update.message.text)
                update.message.reply_text(strings["msg_what_taking_out"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_what[update.message.text]))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

        elif state == 'volunteer-what':
            if any([update.message.text] in keyboard_volunteer_what[i] for i in keyboard_volunteer_what):
                save_data(update.message.chat.id, 'what', update.message.text)
                if have_real_name(update.message.chat.id):
                    # upload_to_exel(update.message.chat.id)
                    user_data = users.find_one({'id': update.message.chat.id})
                    journal.insert_one({'datetime': datetime.datetime.utcnow(),
                                        'type': 'took_out',
                                        'where': user_data['where'],
                                        'what': user_data['what'],
                                        'chat_id': update.message.chat.id})
                    change_user_state(update.message.chat.id, 'main')
                    new_usage(update.message.chat.id)
                    update.message.reply_text(strings["msg_thanks_for_help"], reply_markup=ReplyKeyboardMarkup(keyboard_main))

                else:
                    change_user_state(update.message.chat.id, 'volunteer-who')
                    update.message.reply_text(strings["msg_whats_your_name"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_back))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"])

        elif state == 'volunteer-who':
            change_user_state(update.message.chat.id, 'main')
            save_data(update.message.chat.id, 'real_name', update.message.text)
            user_data = users.find_one({'id': update.message.chat.id})
            journal.insert_one({'datetime': datetime.datetime.utcnow(),
                                'type': 'took_out',
                                'where': user_data['where'],
                                'what': user_data['what'],
                                'chat_id': update.message.chat.id})
            # upload_to_exel(update.message.chat.id)
            new_usage(update.message.chat.id)
            update.message.reply_text(strings["msg_thanks_for_help"], reply_markup=ReplyKeyboardMarkup(keyboard_main))

        elif state == 'overflow-where':
            if update.message.text in keyboard_volunteer_what:
                change_user_state(update.message.chat.id, 'overflow-what')
                save_data(update.message.chat.id, 'where', update.message.text)
                update.message.reply_text(strings["msg_overflow_what"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_what[update.message.text]))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_where))

        elif state == 'overflow-what':
            if any([update.message.text] in keyboard_volunteer_what[i] for i in keyboard_volunteer_what):
                change_user_state(update.message.chat.id, 'main')
                save_data(update.message.chat.id, 'what', update.message.text)
                where = users.find_one({'id': update.message.chat.id})['where']
                journal.insert_one({'datetime': datetime.datetime.utcnow(),
                                    'type': 'report',
                                    'where': where,
                                    'what': update.message.text,
                                    'chat_id': update.message.chat.id})
                new_usage(update.message.chat.id)
                place = report_overflow(update.message.chat.id)
                for i in place['users']:
                    bot = Bot(token=environ.get('TG_TOKEN'))
                    bot.sendMessage(chat_id=int(i), text=strings["msg_overflow_report"].format(place['where'], place['what']))
                update.message.reply_text(strings["msg_thanks_for_help"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"])

        elif state == 'subscription':
            if [update.message.text] in keyboard_subscription:
                change_user_state(update.message.chat.id, 'main')
                if update.message.text == strings["btn_subscribe"]:
                    save_data(update.message.chat.id, 'subscription', True)
                    new_usage(update.message.chat.id)
                    update.message.reply_text(strings["msg_newsletter_subscribed"], reply_markup=ReplyKeyboardMarkup(keyboard_main))

                else:
                    save_data(update.message.chat.id, 'subscription', False)
                    new_usage(update.message.chat.id)
                    update.message.reply_text(strings["msg_newsletter_unsubscribed"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
            else:
                update.message.reply_text(strings["msg_idk_choose_answer_from_menu"])

        elif state == 'annonce':
            change_user_state(update.message.chat.id, 'annonce_confirme')
            bot = Bot(token=environ.get('TG_TOKEN'))
            save_data(update.message.chat.id, 'msg', update.message.text)
            update.message.reply_text(strings["msg_message_will_look_like"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
            bot.sendMessage(chat_id=update.message.chat.id, text=update.message.text)
            update.message.reply_text(strings["msg_announcement_confirm"], reply_markup=ReplyKeyboardMarkup(keyboard_yes_no))

        elif state == 'annonce_confirme':
            if update.message.text == strings["btn_yes"]:
                change_user_state(update.message.chat.id, 'main')
                data = send_announce(update.message.chat.id)
                bot = Bot(token=environ.get('TG_TOKEN'))
                for id, cnt in data['users']:
                    try:
                        bot.sendMessage(chat_id=int(id), text=data['msg'])
                        if int(cnt) == 2:  # TODO why 2??
                            bot.sendMessage(chat_id=int(id), text=strings["msg_you_can_unsubscribe"])
                    except BadRequest as e:
                        print(f"BadRequest: {e} (couldn't send an announcement: id={id}, cnt={cnt}")
                    except Exception as e:
                        print(f"Exception caught of type {type(e)}: {e}\nAnnouncement not sent to id={id}")

                update.message.reply_text(strings["msg_announcement_sent"], reply_markup=ReplyKeyboardMarkup(keyboard_main))
            else:
                change_user_state(update.message.chat.id, 'annonce')
                update.message.reply_text(strings["msg_write_a_message_to_send_out"], reply_markup=ReplyKeyboardMarkup(keyboard_volunteer_back))

    else:
        start(update, context)


def callback_query_triger(update: Update, context: CallbackContext):
    data = update.callback_query.data
    data = data.split('_')
    if data[0] == 'delSub':
        delete_subscription(data[1])
        data = get_users_subscriptions(update.callback_query.message.chat.id)
        key = ([
            [
                InlineKeyboardButton(i['where']+':'+i['what'], callback_data="delSub_"+str(i['_id'])),
            ]
            for i in data])
        if len(key) == 0:
            update.callback_query.edit_message_text(strings["msg_no_subscriptions"], reply_markup=InlineKeyboardMarkup(key))
        else:
            update.callback_query.edit_message_text(strings["msg_choose_to_unsubscribe"], reply_markup=InlineKeyboardMarkup(key))
    if data[0] == 'getStation':
        send_location(update.callback_query.message.chat.id, data[1])


updater = Updater(environ.get('TG_TOKEN'))

updater.dispatcher.add_handler(CommandHandler('start', start))
# updater.dispatcher.add_handler(CommandHandler('help', help))


updater.dispatcher.add_handler(CommandHandler('am_i_admin', am_i_admin))
updater.dispatcher.add_handler(CommandHandler('announce', annonce))

updater.dispatcher.add_handler(MessageHandler(Filters.text, message_triger))
updater.dispatcher.add_handler(CallbackQueryHandler(callback_query_triger,
                                                    run_async=True))


updater.start_polling()
updater.idle()
