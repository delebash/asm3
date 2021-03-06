#!/usr/bin/python

"""
Main ASM search functionality
"""

import animal
import animalcontrol
import configuration
import datetime
import financial
import lostfound
import person
import publishers.base
import time
import users
import waitinglist
from i18n import _, now

THE_PAST = datetime.datetime(1900,1,1,0,0,0)

def search(dbo, session, q):

    """
    Performs a database wide search for the term given.
    special tokens:

    a:term      Only search animals for term
    ac:term     Only search animal control incidents for term
    p:term      Only search people for term
    la:term     Only search lost animals for term
    li:num      Only search licence numbers for term
    fa:term     Only search found animals for term
    wl:term     Only search waiting list entries for term

    sort:az     Sort results alphabetically az
    sort:za     Sort results alphabetically za
    sort:mr     Sort results most recently changed first
    sort:lr     Sort results least recently changed first

    -- update this list in header.js/bind_search/keywords
    activelost, activefound, 
    onshelter/os, notforadoption, hold, holdtoday, quarantine, deceased, 
    forpublish, people, vets, retailers, staff, fosterers, volunteers, 
    shelters, aco, banned, homechecked, homecheckers, members, donors, drivers,
    reservenohomecheck, notmicrochipped

    returns a tuple of:
    results, timetaken, explain, sortname
    """
    # ar (add results) inner method
    def ar(rlist, rtype, sortfield):
        # Return brief records to save bandwidth
        if rtype == "ANIMAL":
            rlist = animal.get_animals_brief(rlist)
        if rtype == "PERSON":
            pass # TODO:
        for r in rlist:
            r["RESULTTYPE"] = rtype
            if sortfield == "RELEVANCE":
                # How "relevant" is this record to what was searched for?
                # animal name and code weight higher than other elements.
                # Note that the code below modifies inbound var q, so by the
                # time we read it here, it should only contain the search term 
                # itself. Weight everything else by last changed date so there
                # is some semblance of useful order for less relevant items
                qlow = q.lower()
                if rtype == "ANIMAL":
                    r["SORTON"] = r["LASTCHANGEDDATE"]
                    if r["SORTON"] is None: r["SORTON"] = THE_PAST 
                    if r["ANIMALNAME"].lower() == qlow or r["SHELTERCODE"].lower() == qlow or r["SHORTCODE"].lower() == qlow:
                        r["SORTON"] = now()
                    # Put matches where term present just behind direct matches
                    elif r["ANIMALNAME"].lower().find(qlow) != -1 or r["SHELTERCODE"].lower().find(qlow) != -1 or r["SHORTCODE"].lower().find(qlow) != -1:
                        r["SORTON"] = now() - datetime.timedelta(seconds=1)
                elif rtype == "PERSON":
                    r["SORTON"] = r["LASTCHANGEDDATE"]
                    if r["SORTON"] is None: r["SORTON"] = THE_PAST
                    # Count how many of the keywords in the search were present
                    # in the owner name field - if it's all of them then raise
                    # the relevance.
                    qw = qlow.split(" ")
                    qm = 0
                    for w in qw:
                        if r["OWNERNAME"].lower().find(w) != -1:
                            qm += 1
                    if qm == len(qw):
                        r["SORTON"] = now()
                    # Put matches where term present just behind direct matches
                    if r["OWNERSURNAME"].lower().find(qlow) or r["OWNERNAME"].lower().find(qlow):
                        r["SORTON"] = now() - datetime.timedelta(seconds=1)
                elif rtype == "LICENCE":
                    r["SORTON"] = r["ISSUEDATE"]
                    if r["SORTON"] is None: r["SORTON"] = THE_PAST
                    if r["LICENCENUMBER"].lower() == qlow: r["SORTON"] = now()
                else:
                    r["SORTON"] = r["LASTCHANGEDDATE"]
            else:
                r["SORTON"] = r[sortfield]
                if r["SORTON"] is None and sortfield.endswith("DATE"): r["SORTON"] = THE_PAST
            results.append(r)

    l = dbo.locale

    # start the clock
    starttime = time.time()

    # The returned results
    results = []
    
    # An i18n explanation of what was searched for
    explain = ""

    # Max records to be returned by search
    limit = configuration.record_search_limit(dbo)

    # Default sort for the search
    searchsort = configuration.search_sort(dbo)

    q = q.replace("'", "`")

    # Allow the sort to be overridden
    if q.find("sort:") != -1:
        if "sort:az" in q:
            searchsort = 0
            q = q.replace("sort:az", "")
        elif "sort:za" in q:
            searchsort = 1
            q = q.replace("sort:za", "")
        elif "sort:lr" in q:
            searchsort = 2
            q = q.replace("sort:lr", "")
        elif "sort:mr" in q:
            searchsort = 3
            q = q.replace("sort:mr", "")
        elif "sort:as" in q:
            searchsort = 4
            q = q.replace("sort:as", "")
        elif "sort:sa" in q:
            searchsort = 5
            q = q.replace("sort:sa", "")
        elif "sort:rel" in q:
            searchsort = 6
            q = q.replace("sort:rel", "")

    q = q.strip()

    # Handle sorting ===========================
    animalsort = ""
    personsort = ""
    wlsort = ""
    acsort = ""
    lasort = ""
    lisort = ""
    fasort = ""
    sortdir = "a"
    sortname = ""
    # alphanumeric ascending
    if searchsort == 0:
        animalsort = "ANIMALNAME"
        personsort = "OWNERNAME"
        wlsort = "OWNERNAME"
        acsort = "OWNERNAME"
        lasort = "OWNERNAME"
        lisort = "OWNERNAME"
        fasort = "OWNERNAME"
        sortdir = "a"
        sortname = _("Alphabetically A-Z", l)
    # alphanumeric descending
    elif searchsort == 1:
        animalsort = "ANIMALNAME"
        personsort = "OWNERNAME"
        wlsort = "OWNERNAME"
        acsort = "OWNERNAME"
        lasort = "OWNERNAME"
        lisort = "OWNERNAME"
        fasort = "OWNERNAME"
        sortdir = "d"
        sortname = _("Alphabetically Z-A", l)
    # last changed ascending
    elif searchsort == 2:
        animalsort = "LASTCHANGEDDATE"
        personsort = "LASTCHANGEDDATE"
        wlsort = "LASTCHANGEDDATE"
        acsort = "LASTCHANGEDDATE"
        lasort = "LASTCHANGEDDATE"
        lisort = "ISSUEDATE"
        fasort = "LASTCHANGEDDATE"
        sortdir = "a"
        sortname = _("Least recently changed", l)
    # last changed descending
    elif searchsort == 3:
        animalsort = "LASTCHANGEDDATE"
        personsort = "LASTCHANGEDDATE"
        acsort = "LASTCHANGEDDATE"
        wlsort = "LASTCHANGEDDATE"
        lasort = "LASTCHANGEDDATE"
        lisort = "ISSUEDATE"
        fasort = "LASTCHANGEDDATE"
        sortdir = "d"
        sortname = _("Most recently changed", l)
    # species ascending
    elif searchsort == 4:
        animalsort = "SPECIESNAME"
        personsort = "OWNERNAME"
        acsort = "SPECIESNAME"
        wlsort = "SPECIESNAME"
        lasort = "SPECIESNAME"
        lisort = "COMMENTS"
        fasort = "SPECIESNAME"
        sortdir = "a"
        sortname = _("Species A-Z", l)
    elif searchsort == 5:
        animalsort = "SPECIESNAME"
        personsort = "OWNERNAME"
        acsort = "SPECIESNAME"
        wlsort = "SPECIESNAME"
        lasort = "SPECIESNAME"
        lisort = "COMMENTS"
        fasort = "SPECIESNAME"
        sortdir = "d"
        sortname = _("Species Z-A", l)
    elif searchsort == 6:
        animalsort = "RELEVANCE"
        personsort = "RELEVANCE"
        wlsort = "RELEVANCE"
        acsort = "RELEVANCE"
        lasort = "RELEVANCE"
        lisort = "RELEVANCE"
        fasort = "RELEVANCE"
        sortdir = "d"
        sortname = _("Most relevant", l)

    viewperson = users.check_permission_bool(session, users.VIEW_PERSON)
    viewanimal = users.check_permission_bool(session, users.VIEW_ANIMAL)
    viewstaff = users.check_permission_bool(session, users.VIEW_STAFF)
    viewvolunteer = users.check_permission_bool(session, users.VIEW_VOLUNTEER)
    user = session.user
    locationfilter = session.locationfilter
    siteid = session.siteid
    visibleanimalids = session.visibleanimalids

    # Special token searches
    if q == "onshelter" or q == "os":
        explain = _("All animals on the shelter.", l)
        if viewanimal:
            ar(animal.get_animal_find_simple(dbo, "", limit=limit, locationfilter=locationfilter, siteid=siteid, visibleanimalids=visibleanimalids), "ANIMAL", animalsort)

    elif q == "notforadoption":
        explain = _("All animals who are flagged as not for adoption.", l)
        if viewanimal:
            ar(animal.get_animals_not_for_adoption(dbo), "ANIMAL", animalsort)

    elif q == "longterm":
        explain = _("All animals who have been on the shelter longer than {0} months.", l).format(configuration.long_term_months(dbo))
        if viewanimal:
            ar(animal.get_animals_long_term(dbo), "ANIMAL", animalsort)

    elif q == "notmicrochipped":
        explain = _("All animals who have not been microchipped", l)
        if viewanimal:
            ar(animal.get_animals_not_microchipped(dbo), "ANIMAL", animalsort)

    elif q == "hold":
        explain = _("All animals who are currently held in case of reclaim.", l)
        if viewanimal:
            ar(animal.get_animals_hold(dbo), "ANIMAL", animalsort)

    elif q == "holdtoday":
        explain = _("All animals where the hold ends today.", l)
        if viewanimal:
            ar(animal.get_animals_hold_today(dbo), "ANIMAL", animalsort)

    elif q == "quarantine":
        explain = _("All animals who are currently quarantined.", l)
        if viewanimal:
            ar(animal.get_animals_quarantine(dbo), "ANIMAL", animalsort)

    elif q == "deceased":
        explain = _("Recently deceased shelter animals (last 30 days).", l)
        if viewanimal:
            ar(animal.get_animals_recently_deceased(dbo), "ANIMAL", animalsort)

    elif q == "forpublish":
        explain = _("All animals matching current publishing options.", l)
        if viewanimal:
            ar(publishers.base.get_animal_data(dbo), "ANIMAL", animalsort)

    elif q == "people":
        ar(person.get_person_find_simple(dbo, "", user, classfilter="all", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)
        explain = _("All people on file.", l)

    elif q == "vets":
        explain = _("All vets on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="vet", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "retailers":
        explain = _("All retailers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="retailer", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "staff":
        explain = _("All staff on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="staff", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "fosterers":
        explain = _("All fosterers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="fosterer", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "volunteers":
        explain = _("All volunteers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="volunteer", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "shelters":
        explain = _("All animal shelters on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="shelter", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "aco":
        explain = _("All animal care officers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="aco", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "banned":
        explain = _("All banned owners on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="banned", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "homechecked":
        explain = _("All homechecked owners on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="homechecked", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "homecheckers":
        explain = _("All homecheckers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="homechecker", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "members":
        explain = _("All members on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="member", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "donors":
        explain = _("All donors on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="donor", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "drivers":
        explain = _("All drivers on file.", l)
        if viewperson:
            ar(person.get_person_find_simple(dbo, "", user, classfilter="driver", includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort)

    elif q == "reservenohomecheck":
        explain = _("People with active reservations, but no homecheck has been done.", l)
        if viewperson:
            ar(person.get_reserves_without_homechecks(dbo), "PERSON", personsort)

    elif q == "overduedonations":
        explain = _("People with overdue donations.", l)
        if viewperson:
            ar(person.get_overdue_donations(dbo), "PERSON", personsort)

    elif q == "activelost":
        explain = _("Lost animals reported in the last 30 days.", l)
        if users.check_permission_bool(session, users.VIEW_LOST_ANIMAL):
            ar(lostfound.get_lostanimal_find_simple(dbo, "", limit=limit, siteid=siteid), "LOSTANIMAL", lasort)

    elif q == "activefound":
        explain = _("Found animals reported in the last 30 days.", l)
        if users.check_permission_bool(session, users.VIEW_FOUND_ANIMAL):
            ar(lostfound.get_foundanimal_find_simple(dbo, "", limit=limit, siteid=siteid), "FOUNDANIMAL", fasort)

    elif q.startswith("a:") or q.startswith("animal:"):
        q = q[q.find(":")+1:].strip()
        explain = _("Animals matching '{0}'.", l).format(q)
        if viewanimal:
            ar( animal.get_animal_find_simple(dbo, q, limit=limit, locationfilter=locationfilter, siteid=siteid, visibleanimalids=visibleanimalids), "ANIMAL", animalsort )

    elif q.startswith("ac:") or q.startswith("animalcontrol:"):
        q = q[q.find(":")+1:].strip()
        explain = _("Animal control incidents matching '{0}'.", l).format(q)
        if users.check_permission_bool(session, users.VIEW_INCIDENT):
            ar( animalcontrol.get_animalcontrol_find_simple(dbo, q, user, limit=limit, siteid=siteid), "ANIMALCONTROL", acsort )

    elif q.startswith("p:") or q.startswith("person:"):
        q = q[q.find(":")+1:].strip()
        explain = _("People matching '{0}'.", l).format(q)
        if viewperson:
            ar( person.get_person_find_simple(dbo, q, user, includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort )

    elif q.startswith("wl:") or q.startswith("waitinglist:"):
        q = q[q.find(":")+1:].strip()
        explain = _("Waiting list entries matching '{0}'.", l).format(q)
        if users.check_permission_bool(session, users.VIEW_WAITING_LIST):
            ar( waitinglist.get_waitinglist_find_simple(dbo, q, limit=limit, siteid=siteid), "WAITINGLIST", wlsort )

    elif q.startswith("la:") or q.startswith("lostanimal:"):
        q = q[q.find(":")+1:].strip()
        explain = _("Lost animal entries matching '{0}'.", l).format(q)
        if users.check_permission_bool(session, users.VIEW_LOST_ANIMAL):
            ar( lostfound.get_lostanimal_find_simple(dbo, q, limit=limit, siteid=siteid), "LOSTANIMAL", lasort )

    elif q.startswith("fa:") or q.startswith("foundanimal:"):
        q = q[q.find(":")+1:].strip()
        explain = _("Found animal entries matching '{0}'.", l).format(q)
        if users.check_permission_bool(session, users.VIEW_FOUND_ANIMAL):
            ar( lostfound.get_foundanimal_find_simple(dbo, q, limit=limit, siteid=siteid), "FOUNDANIMAL", fasort )

    elif q.startswith("li:") or q.startswith("license:"):
        q = q[q.find(":")+1:].strip()
        explain = _("License numbers matching '{0}'.", l).format(q)
        if users.check_permission_bool(session, users.VIEW_LICENCE):
            ar( financial.get_licence_find_simple(dbo, q, limit), "LICENCE", lisort )

    # No special tokens, search everything and collate
    else:
        if viewanimal:
            ar( animal.get_animal_find_simple(dbo, q, limit=limit, locationfilter=locationfilter, siteid=siteid, visibleanimalids=visibleanimalids), "ANIMAL", animalsort )
        if users.check_permission_bool(session, users.VIEW_INCIDENT):
            ar( animalcontrol.get_animalcontrol_find_simple(dbo, q, user, limit=limit, siteid=siteid), "ANIMALCONTROL", acsort )
        if viewperson:
            ar( person.get_person_find_simple(dbo, q, user, includeStaff=viewstaff, includeVolunteers=viewvolunteer, limit=limit, siteid=siteid), "PERSON", personsort )
        if users.check_permission_bool(session, users.VIEW_WAITING_LIST):
            ar( waitinglist.get_waitinglist_find_simple(dbo, q, limit=limit, siteid=siteid), "WAITINGLIST", wlsort )
        if users.check_permission_bool(session, users.VIEW_LOST_ANIMAL):
            ar( lostfound.get_lostanimal_find_simple(dbo, q, limit=limit, siteid=siteid), "LOSTANIMAL", lasort )
        if users.check_permission_bool(session, users.VIEW_FOUND_ANIMAL):
            ar( lostfound.get_foundanimal_find_simple(dbo, q, limit=limit, siteid=siteid), "FOUNDANIMAL", fasort )
        if users.check_permission_bool(session, users.VIEW_LICENCE):
            ar( financial.get_licence_find_simple(dbo, q, limit), "LICENCE", lisort )
        explain = _("Results for '{0}'.", l).format(q)

    # Apply the sort to the results
    if sortdir == "a":
        sortresults = sorted(results, key=lambda k: k["SORTON"])
    else:
        sortresults = sorted(results, reverse=True, key=lambda k: k["SORTON"])

    # stop the clock
    timetaken = (time.time() - starttime)

    # Return our final set of values
    return sortresults, timetaken, explain, sortname

