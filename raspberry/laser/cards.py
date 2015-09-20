import sqlite3 
from cardsdb import CardsDB 
import curses
import npyscreen
import rfid

#----------------------------------------------------------------------------
#
#  Cards List
#
#----------------------------------------------------------------------------
class CardList(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(CardList, self).__init__(*args, **keywords)
        self.add_handlers({
            "^A": self.when_add_record,
            "^D": self.when_delete_record
        })

    def display_value(self, vl):
        return "%s, %s" % (vl[1], vl[2])

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('EDITRECORDFM').value =act_on_this[0]
        self.parent.parentApp.switchForm('EDITRECORDFM')

    def when_add_record(self, *args, **keywords):
        self.parent.parentApp.getForm('EDITRECORDFM').value = None
        self.parent.parentApp.switchForm('EDITRECORDFM')

    def when_delete_record(self, *args, **keywords):
        self.parent.parentApp.myDatabase.delete_card(self.values[self.cursor_line][0])
        self.parent.update_list()

#----------------------------------------------------------------------------
#
#  Main Form ; List cards
#
#----------------------------------------------------------------------------
class CardListDisplay(npyscreen.ActionFormWithMenus):
    #MAIN_WIDGET_CLASS = CardList
    def create(self):
        self.cardUID = "";
        self.lCards = self.add(CardList, name="Cards", width=70, height=24)
        self.m1 = self.add_menu(name="Main Menu")
        self.m1.addItemsFromList([
            ("Karte einlesen",   self.readCard),
            ("Exit", self.exit_application),
        ]) 

    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        #self.wMain.values = self.parentApp.myDatabase.list_all_cards()
        self.lCards.values = self.parentApp.myDatabase.list_all_cards()
        self.lCards.display()

    def on_ok(self):
        curses.beep()

    def exit_application(self):
        curses.beep()
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.switchFormNow()

    def readCard(self):
        while True:
            rfid.waitTag()
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                id = self.parentApp.myDatabase.cardExists(uid)
                if (id >= 0):
                    self.parentApp.getForm('EDITRECORDFM').value = id
                else:
                    self.parentApp.getForm('EDITRECORDFM').value = -1
                break
            else:
                self.cardUID = ""
                break

        #self.parent.parentApp.getForm('EDITRECORDFM').value =act_on_this[0]
        self.parentApp.switchForm('EDITRECORDFM')

#----------------------------------------------------------------------------
#
#  Card data editor
#
#----------------------------------------------------------------------------
class EditCard(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.tVorname   = self.add(npyscreen.TitleText, name = "Vorname:",)
        self.tNachname = self.add(npyscreen.TitleText, name = "Nachname:")
        self.tUnits      = self.add(npyscreen.TitleText, name = "Units:")
        self.active = 1;

    def beforeEditing(self):
        if self.value>= 0 :
            record = self.parentApp.myDatabase.get_card(self.value)
            self.name = "Karte id : %s" % record[0]
            self.id          = record[0]
            self.tVorname.value   = record[1]
            self.tNachname.value = record[2]
            self.tUnits.value      = str(record[3])
            self.active      = record[4]
        else:
            self.name = "Neue Karte anlegen:"
            self.id          = ''
            self.tVorname.value   = ''
            self.tNachname.value = ''
            self.tUnits.value      = ''
            self.active      = 1;

    def on_ok(self):
        if self.id: # We are editing an existing record
            self.parentApp.myDatabase.update_card(self.id,
                                            vorname=self.tVorname.value,
                                            nachname = self.tNachname.value,
                                            units = self.tUnits.value,
                                            active = 1,
                                            )
        else: # We are adding a new record.
            self.parentApp.myDatabase.add_card(vorname=self.tVorname.value,
            nachname = self.tNachname.value,
            units = self.tUnits.value,
            )
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

#----------------------------------------------------------------------------
#
#  Wait until Card cam be read and return uid
#
#----------------------------------------------------------------------------
class rfidReader():
    def do():
        while True:
            rfid.waitTag()
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                if self.myDatabase.cardExists(uid):
                    print('Card found:'+uid)
                else:
                    print('Card NOT found:'+uid)

#----------------------------------------------------------------------------
#
# Laseradmin
# - wait until a card is hold to the reader
# - read card uid
# check if card uid is in database
# if yes -> show record
# if no, issue new record
# update or insert
# go to read card
#
#----------------------------------------------------------------------------
class LaserAdmin(npyscreen.NPSAppManaged):
    def onStart(self):
        self.myDatabase = CardsDB()
        self.addForm("MAIN", CardListDisplay)
        self.addForm("EDITRECORDFM", EditCard)

if __name__ == '__main__':
    myApp = LaserAdmin()
    myApp.run()
