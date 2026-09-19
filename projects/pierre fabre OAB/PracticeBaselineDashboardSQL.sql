# Baseline Dashboard SQL Logic

# Query:
select COUNT(O2PR_ID) as PatientsIdentifiedInBaseline,
       sum(O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1) as PatientsEligibleForReviewAfterScreening,
       current_date as ReportDate,
       LOC_Name as Practice,
       LOC_NHSID as NHSID
from oab2PatientResults
left join Reviews on R_ID = O2PR_EventID
left join Events on EVENT_ReviewID = R_ID
left join Locations on LOC_ID = R_LocID
where EVENT_ID = ${EventID}

# Chart: Patients identified in baseline search results
# Query 1:
select
	(case a.TN_ID when 1 then '0-17'
	 when 2 then '18-29'
	 when 3 then '30-39'
	 when 4 then '40-49'
	 when 5 then '50-59'
	 when 6 then '60-69'
	 when 7 then '70-79'
	 when 8 then '80-89'
	 when 9 then '90+' end) as Ages,
	(case b.TN_ID when 1 then 'Male' when 2 then 'Female' end) as Sex,
	(case b.TN_ID
	 when 1 then sum(case a.TN_ID when 1 then O2PR_Gender = 1 and O2PR_Age between 0 and 17
	 when 2 then O2PR_Gender = 1 and O2PR_Age between 18 and 29
	 when 3 then O2PR_Gender = 1 and O2PR_Age between 30 and 39
	 when 4 then O2PR_Gender = 1 and O2PR_Age between 40 and 49
	 when 5 then O2PR_Gender = 1 and O2PR_Age between 50 and 59
	 when 6 then O2PR_Gender = 1 and O2PR_Age between 60 and 69
	 when 7 then O2PR_Gender = 1 and O2PR_Age between 70 and 79
	 when 8 then O2PR_Gender = 1 and O2PR_Age between 80 and 89
	 when 9 then O2PR_Gender = 1 and O2PR_Age >= 90 end)
	 when 2 then sum(case a.TN_ID when 1 then O2PR_Gender = 2 and O2PR_Age between 0 and 17
	 when 2 then O2PR_Gender = 2 and O2PR_Age between 18 and 29
	 when 3 then O2PR_Gender = 2 and O2PR_Age between 30 and 39
	 when 4 then O2PR_Gender = 2 and O2PR_Age between 40 and 49
	 when 5 then O2PR_Gender = 2 and O2PR_Age between 50 and 59
	 when 6 then O2PR_Gender = 2 and O2PR_Age between 60 and 69
	 when 7 then O2PR_Gender = 2 and O2PR_Age between 70 and 79
	 when 8 then O2PR_Gender = 2 and O2PR_Age between 80 and 89
	 when 9 then O2PR_Gender = 2 and O2PR_Age >= 90
	 end)
	end) as Total
from oab2PatientResults
left join Reviews on R_ID = O2PR_EventID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 9 and b.TN_ID <= 2 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;


# Query 2:
select
	(case TN_ID when 1 then '0-17'
	 when 2 then '18-29'
	 when 3 then '30-39'
	 when 4 then '40-49'
	 when 5 then '50-59'
	 when 6 then '60-69'
	 when 7 then '70-79'
	 when 8 then '80-89'
	 when 9 then '90+' end) as Ages,
(case TN_ID
	 when 1 then sum(O2PR_Age between 0 and 17)
	 when 2 then sum(O2PR_Age between 18 and 29)
	 when 3 then sum(O2PR_Age between 30 and 39)
	 when 4 then sum(O2PR_Age between 40 and 49)
	 when 5 then sum(O2PR_Age between 50 and 59)
	 when 6 then sum(O2PR_Age between 60 and 69)
	 when 7 then sum(O2PR_Age between 70 and 79)
	 when 8 then sum(O2PR_Age between 80 and 89)
	 when 9 then sum(O2PR_Age >= 90)
	 end) as Total
from oab2PatientResults
left join Reviews on R_ID = O2PR_EventID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 9 and EVENT_ID = ${EventID} and (O2PR_Gender is not null)
group by TN_ID;


# Chart: Patients meeting protocol inclusion criteria
select
	(case a.TN_ID when 1 then '0-17'
	            when 2 then '18-29'
	            when 3 then '30-39'
	            when 4 then '40-49'
	            when 5 then '50-59'
	            when 6 then '60-69'
	            when 7 then '70-79'
	            when 8 then '80-89'
	            when 9 then '90+' end) as Ages,
	(case b.TN_ID when 1 then 'Male' when 2 then 'Female' end) as Sex,
	(case b.TN_ID
	    when 1 then sum(case a.TN_ID when 1 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 0 and 17
	                 when 2 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 18 and 29
	                 when 3 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 30 and 39
	                 when 4 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 40 and 49
	                 when 5 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 50 and 59
	                 when 6 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 60 and 69
	                 when 7 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 70 and 79
	                 when 8 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age between 80 and 89
	                 when 9 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 1 and O2PR_Age >= 90 end)
	    when 2 then sum(case a.TN_ID when 1 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 0 and 17
	                 when 2 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 18 and 29
	                 when 3 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 30 and 39
	                 when 4 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 40 and 49
	                 when 5 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 50 and 59
	                 when 6 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 60 and 69
	                 when 7 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 70 and 79
	                 when 8 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age between 80 and 89
	                 when 9 then O2PR_InCohort01 = 1 and O2PR_AuthorisedForReview = 1 and O2PR_Gender = 2 and O2PR_Age >= 90
	        end)

	end) as Total
from oab2PatientResults
left join Reviews on R_ID = O2PR_EventID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 9 and b.TN_ID <= 2 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;






# Chart: Patients meeting clinical protocol cohort criteria

select
	(case TN_ID when 1 then 'Cohort 1' when 2 then 'Cohort 2' when 3 then 'Cohort 3' when 4 then 'Cohort 4' end) as Type,
	(case TN_ID when 1 then sum(O2PR_Cohort01234 = 1 and O2PR_AuthorisedForReview = 1)
	 when 2 then sum(O2PR_Cohort01234 = 2 and O2PR_AuthorisedForReview = 1)
	 when 3 then sum(O2PR_Cohort01234 = 3 and O2PR_AuthorisedForReview = 1)
	 when 4 then sum(O2PR_Cohort01234 = 4 and O2PR_AuthorisedForReview = 1) end) as Total
from oab2PatientResults
left join Reviews on R_ID = O2PR_EventID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 4 and EVENT_ID = ${EventID}
group by TN_ID;

