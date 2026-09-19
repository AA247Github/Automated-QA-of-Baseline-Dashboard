#ASTHMA PREVALENCE & REGISTER ANALYSIS
#Comparison of practice QOF prevalence with Sub-ICB/Health board and national
select
	(case TN_ID when 1 then (case when Prac = l.LOC_ID then 'Current practice prevalence' end)
	            when 2 then (case when Prac = l.LOC_ID then 'Practice prevalence*' end)
	            when 3 then (case when CCG = p.LOC_ID then 'sub-ICB prevalence*' end)
	            when 4 then (case when Country = (case when c.LOC_ID in (9617, 9618, 14369) then c.LOC_ID else 14303 end) then 'National prevalence*' end)
		end) as Type,
	(case TN_ID when 1 then Patients / l.LOC_ListSize
	            else sum(QR_RegisterSize) / sum(QL_ListSize) end) as Total
from Locations c
inner join (select
	            R_LocID as Prac,
	            p.LOC_ID as CCG,
	            (case when c.LOC_ID in (9617, 9618, 14369) then c.LOC_ID else 14303 end) as Country,
	            count(1) as Patients
            from DialInAsthma2PatientResults
            left join DialIns on DIALIN_ID = A2PR_DialInID
            left join Reviews on R_PreDataExtract = DIALIN_ID
            left join Events on EVENT_ReviewID = R_ID
            left join Locations l on l.LOC_ID = R_LocID
            left join Locations p on p.LOC_ID = l.LOC_Parent
            left join Locations c on c.LOC_ID = p.LOC_Parent
            where EVENT_ID = ${EventID}) a on Country = (case when c.LOC_ID in (9617, 9618, 14369) then c.LOC_ID else 14303 end)
join (select
	      max(QY_ID) as YearID
      from Reviews
      left join Events on EVENT_ReviewID = R_ID
      left join QOFListSizes on QL_LocationID = R_LocID
      left join QOFYear on QY_ID = QL_YearID and QY_EndDate <= R_EndDate
      where EVENT_ID = ${EventID}) b
left join Locations p on c.LOC_ID = p.LOC_Parent
left join Locations l on p.LOC_ID = l.LOC_Parent
left join QOFRegisters on l.LOC_ID = QR_LocationID and QR_YearID = YearID and QR_DomainID = 1
left join QOFListSizes on QL_LocationID = QR_LocationID and QL_YearID = YearID
join tbl_Numbers
where TN_ID <= 4
group by Type, TN_ID
having Type is not null
order by TN_ID;

#Evidence of tests for asthma diagnosis (all patients on the asthma register
select
	(case a.TN_ID when 1 then 'Record of any test' when 2 then 'No record of test' end) as Tests,

	(case b.TN_ID when 1 then 'FeNO' when 2 then 'Eosinophils' when 3 then 'Spirometry' when 4 then 'PEFR' end) as Type,

	(case a.TN_ID when 1 then (case b.TN_ID
	                                        when 1 then sum(A2PR_Feno12m > 0)
	                                        when 2 then sum(A2PR_EosinophilDate is not null)
	                                        when 3 then sum(A2PR_Spirometry12Mo > 0)
	                                        when 4 then sum(A2PR_PeakFlow12m > 0)
	    end)

	              when 2 then (case b.TN_ID
	                                        when 1 then sum(A2PR_Feno12m = 0)
	                                        when 2 then sum(A2PR_EosinophilDate is null)
	                                        when 3 then sum(A2PR_Spirometry12Mo = 0)
	                                        when 4 then sum(A2PR_PeakFlow12m = 0)
	                            end) end) as total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 4 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Demographic analysis (taking into account gender and age)
select
	(case TN_ID when 1 then 'Male' when 2 then 'Female' end) as Sex,
	sum(case TN_ID when 1 then A2PR_Gender = 1 when 2 then A2PR_Gender = 2 end) as Total
from DialInAsthma2PatientResults
left join uploadGenderList on UGL_ID = A2PR_Gender and UGL_Default = 1
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

#Evidence of tests for asthma diagnosis (diagnosis of asthma since April 2025)
select
	(case a.TN_ID when 1 then 'Record of any test' when 2 then 'No record of test' end) as Tests,

	(case b.TN_ID when 1 then 'FeNO' when 2 then 'Eosinophils' when 3 then 'Spirometry' when 4 then 'PEFR' end) as Type,


	(case a.TN_ID when 1 then (case b.TN_ID
	                                        when 1 then sum(A2PR_NdxFeno > 0 and A2PR_NewDiagAst12m = 1)
	                                        when 2 then sum(A2PR_NdxEos > 0 and A2PR_NewDiagAst12m = 1)
	                                        when 3 then sum(A2PR_NdxSpiro > 0 and A2PR_NewDiagAst12m = 1)
	                                        when 4 then sum(A2PR_NdxPefr > 0 and A2PR_NewDiagAst12m = 1)
	    end)

	              when 2 then (case b.TN_ID
	                                        when 1 then sum(A2PR_NdxFeno = 0 and A2PR_NewDiagAst12m = 1)
	                                        when 2 then sum(A2PR_NdxEos = 0 and A2PR_NewDiagAst12m = 1)
	                                        when 3 then sum(A2PR_NdxSpiro = 0 and A2PR_NewDiagAst12m = 1)
	                                        when 4 then sum(A2PR_NdxPefr = 0 and A2PR_NewDiagAst12m = 1)
	                  end) end) as total


from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 4 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Age bands with respect to gender
select
	(case TN_ID when 1 then '0-5'
	            when 2 then '6-10'
	            when 3 then '11-15'
	            when 4 then '16-20'
	            when 5 then '21-30'
	            when 6 then '31-40'
	            when 7 then '41-50'
	            when 8 then '51-60'
	            when 9 then '61-70'
	            when 10 then '71-80'
	            when 11 then '81 and over' end) as Ages,
	sum(case TN_ID when 1 then A2PR_Age between 0 and 5
	               when 2 then A2PR_Age between 6 and 10
	               when 3 then A2PR_Age between 11 and 15
	               when 4 then A2PR_Age between 16 and 20
	               when 5 then A2PR_Age between 21 and 30
	               when 6 then A2PR_Age between 31 and 40
	               when 7 then A2PR_Age between 41 and 50
	               when 8 then A2PR_Age between 51 and 60
	               when 9 then A2PR_Age between 61 and 70
	               when 10 then A2PR_Age between 71 and 80
	               when 11 then A2PR_Age >= 81 end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 11 and EVENT_ID = ${EventID}
group by TN_ID;

select
	(case a.TN_ID when 1 then '0-5'
	              when 2 then '6-10'
	              when 3 then '11-15'
	              when 4 then '16-20'
	              when 5 then '21-30'
	              when 6 then '31-40'
	              when 7 then '41-50'
	              when 8 then '51-60'
	              when 9 then '61-70'
	              when 10 then '71-80'
	              when 11 then '81 and over' end) as Ages,
	(case b.TN_ID when 1 then 'Male' when 2 then 'Female' end) as Sex,
	sum((case a.TN_ID when 1 then A2PR_Age between 0 and 5
	                 when 2 then A2PR_Age between 6 and 10
	                 when 3 then A2PR_Age between 11 and 15
	                 when 4 then A2PR_Age between 16 and 20
	                 when 5 then A2PR_Age between 21 and 30
	                 when 6 then A2PR_Age between 31 and 40
	                 when 7 then A2PR_Age between 41 and 50
	                 when 8 then A2PR_Age between 51 and 60
	                 when 9 then A2PR_Age between 61 and 70
	                 when 10 then A2PR_Age between 71 and 80
	                 when 11 then A2PR_Age >= 81 end) and (case b.TN_ID when 1 then A2PR_Gender = 1 when 2 then A2PR_Gender =  2 end)) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 11 and b.TN_ID <= 2 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;


#Prevalence of co-morbidities in patients with asthma
select
	convert((case TN_ID when 1 then 'COPD'
	                    when 2 then 'Rhinitis'
	                    when 3 then 'GORD'
	                    when 4 then concat('Obesity (BMI',char(14846373),'30)')
	                    when 5 then 'Depression or Anxiety' end) using utf8) as Type,

	(case TN_ID when 1 then (sum(A2PR_Copd is not null) / count(A2PR_ID))
	            when 2 then (sum(A2PR_Rhinitis10 = 1) / count(A2PR_ID))
	            when 3 then (sum(A2PR_Gord10 = 1) / count(A2PR_ID))
	            when 4 then (sum(A2PR_BMI >= 30) / count(A2PR_ID))
	            when 5 then (sum(A2PR_Dep is not null)/count(A2PR_ID)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 5 and EVENT_ID = ${EventID}
group by TN_ID;


#Length of time since last recorded asthma review (months)
select
	(case TN_ID when 1 then 'with'
	            when 2 then 'without' end) as Review,
	(case TN_ID when 1 then sum(A2PR_AstReview12Mo = 2)
	            when 2 then sum(A2PR_AstReview12Mo in (1, 0)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

select
	(case TN_ID when 1 then '<1'
	            when 2 then '1 - 3'
	            when 3 then '4 - 6'
	            when 4 then '7 - 9'
	            when 5 then '10 - 12'
	            when 6 then '13 - 24'
	            when 7 then '>24'
	            when 8 then 'No record' end) as Months,

	(case TN_ID when 1 then sum(A2PR_MonthsSinceLR < 1)
	            when 2 then sum(A2PR_MonthsSinceLR in (1, 2, 3))
	            when 3 then sum(A2PR_MonthsSinceLR in (4, 5, 6))
	            when 4 then sum(A2PR_MonthsSinceLR in (7, 8, 9))
	            when 5 then sum(A2PR_MonthsSinceLR in (10, 11, 12))
	            when 6 then sum(A2PR_MonthsSinceLR between 13 and 24)
	            when 7 then sum(A2PR_MonthsSinceLR > 24)
	            when 8 then sum(A2PR_MonthsSinceLR is null) end) as Total

from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 8 and EVENT_ID = ${EventID}
group by TN_ID;

#BASELINE ASTHMA CARE MARKERS (INCLUDES ALL PATIENTS ON THE ASTHMA REGISTER)
#Assessment of management against NICE or QOF indicators within past 12 months
select

	(case a.TN_ID when 1 then 'Yes' when 2 then 'No' end) as YN,

	(case b.TN_ID when 1 then 'Asthma review'
	              when 2 then 'Assessment of asthma control'
	              when 3 then 'Record of exacerbations'
	              when 4 then 'Assessment of inhaler technique'
	              when 5 then 'Written PAAP'
	              when 6 then 'Asthma review meeting all criteria' end) as type,

	(case a.TN_ID when 1 then (case b.TN_ID when 1 then ifnull(sum(A2PR_AstReview12Mo = 2) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_ActScore12Mo = 2 or A2PR_AcqScore12m = 2) / count(A2PR_ID),0)
	                                        when 3 then ifnull(sum(A2PR_RecExacerb = 2) / count(A2PR_ID),0)
	                                        when 4 then ifnull(sum(A2PR_InhalerTech12Mo = 2) / count(A2PR_ID),0)
	                                        when 5 then ifnull(sum(A2PR_Paap12Mo = 2) / count(A2PR_ID),0)
	                                        when 6 then ifnull(sum(A2PR_AstReview12Mo = 2 and A2PR_ActScore12Mo = 2 and A2PR_RecExacerb = 2 and A2PR_InhalerTech12Mo = 2 and A2PR_Paap12Mo = 2) /
	                                                           count(A2PR_ID),0)
		end)

	              when 2 then (case b.TN_ID when 1 then ifnull(sum(A2PR_AstReview12Mo in (1, 0)) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_ActScore12Mo <> 2 and A2PR_AcqScore12m <> 2 ) / count(A2PR_ID),0)
	                                        when 3 then ifnull(sum(A2PR_RecExacerb in (1, 0)) / count(A2PR_ID),0)
	                                        when 4 then ifnull(sum(A2PR_InhalerTech12Mo in (1, 0)) / count(A2PR_ID),0)
	                                        when 5 then ifnull(sum(A2PR_Paap12Mo in (1, 0)) / count(A2PR_ID),0)
	                                        when 6 then ifnull((count(A2PR_ID) -
	                                                            sum(A2PR_AstReview12Mo = 2 and A2PR_ActScore12Mo = 2 and A2PR_RecExacerb = 2 and A2PR_InhalerTech12Mo = 2 and A2PR_Paap12Mo = 2)) /
	                                                           count(A2PR_ID),0) end) end) as total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 6 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Other key markers relevant to asthma (past 12M)
select

	(case a.TN_ID when 1 then 'Yes' when 2 then 'No' end) as YN,

	(case b.TN_ID
	              when 1 then 'FeNO'
	              when 2 then 'SABA use recorded'
	              when 3 then 'Smoking status recorded'
	    	      when 4 then 'Peak flow recorded'
	    end) as type,

	(case a.TN_ID when 1 then (case b.TN_ID

	                                        when 1 then ifnull(sum(A2PR_Feno12m = 2) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_SabaUseRecord12Mo = 2) / count(A2PR_ID),0)
	                                        when 3 then ifnull(sum(A2PR_SmokingStat12Mo = 2) / count(A2PR_ID),0)
	                                        when 4 then ifnull(sum(A2PR_PeakFlow12m = 2) / count(A2PR_ID),0)
	    end)

	              when 2 then (case b.TN_ID

	                                        when 1 then ifnull(sum(A2PR_Feno12m in (1, 0)) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_SabaUseRecord12Mo in (1, 0)) / count(A2PR_ID),0)
	                                        when 3 then ifnull(sum(A2PR_SmokingStat12Mo in (1, 0)) / count(A2PR_ID),0)
	                                        when 4 then ifnull(sum(A2PR_PeakFlow12m in (1, 0)) / count(A2PR_ID),0)
	                  end) end) as total
from asthma2PatientResults
left join Reviews
on R_ID = A2PR_EventID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 4 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Record of vaccinations
select

	(case a.TN_ID when 1 then 'Yes' when 2 then 'No' end) as YN,

	(case b.TN_ID when 1 then 'Flu Vaccination in last vaccination period'
	              when 2 then 'Pneumococcal vaccination ever' end) as type,

	(case a.TN_ID when 1 then (case b.TN_ID when 1 then ifnull(sum(A2PR_FlucVaccCurrent = 2) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_PneumoVaccEver = 1) / count(A2PR_ID),0) end)

	              when 2 then (case b.TN_ID when 1 then ifnull(sum(A2PR_FlucVaccCurrent in (1, 0)) / count(A2PR_ID),0)
	                                        when 2 then ifnull(sum(A2PR_PneumoVaccEver = 0) / count(A2PR_ID),0) end) end) as total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 2 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Latest recorded smoking status
select
	(case TN_ID when 1 then 'WITH' when 2 then 'WITHOUT' end) as Review,
	(case TN_ID when 1 then sum(A2PR_SmokingStat12Mo = 2)
	            when 2 then sum(A2PR_SmokingStat12Mo in (1, 0)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

select
	(case TN_ID when 1 then 'Smoker' when 2 then 'Past smoker' when 3 then 'Never smoked' when 4 then 'No record' end) as Type,

	(case TN_ID when 1 then sum(A2PR_SmokingStatcalc = 3)
	            when 2 then sum(A2PR_SmokingStatcalc in (1, 4))
	            when 3 then sum(A2PR_SmokingStatcalc = 2)
	            when 4 then sum(A2PR_SmokingStatcalc = 5 or A2PR_SmokingStatcalc is null) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 4 and EVENT_ID = ${EventID}
group by TN_ID;

#Offer of smoking cessation (current smokers)
select
	(case TN_ID when 1 then 'Offer in past 12M'
	            when 2 then 'Offer over 12M ago'
	            when 3 then 'No record' end) as Type,

	(case TN_ID when 1 then sum(A2PR_SmokingStatcalc = 3 and A2PR_SmokingCess12m = 2)
	            when 2 then sum(A2PR_SmokingStatcalc = 3 and A2PR_SmokingCess12m = 1)
	            when 3 then sum(A2PR_SmokingStatcalc = 3 and A2PR_SmokingCess12m = 0) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 3 and EVENT_ID = ${EventID}
group by TN_ID;


#Latest recorded inhaler technique
select
	(case TN_ID when 1 then 'Good'
	            when 2 then 'Moderate'
	            when 3 then 'Poor'
	            when 4 then 'No record' end) as Type,

	(case TN_ID when 1 then sum(A2PR_InhalerTechCalc = 3)
	            when 2 then sum(A2PR_InhalerTechCalc = 2)
	            when 3 then sum(A2PR_InhalerTechCalc = 1)
	            when 4 then sum(A2PR_InhalerTechCalc is null) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 4 and EVENT_ID = ${EventID}
group by TN_ID;

select
	(case TN_ID when 1 then 'WITH' when 2 then 'WITHOUT' end) as Review,
	(case TN_ID when 1 then sum(A2PR_InhalerTech12Mo = 2)
	            when 2 then sum(A2PR_InhalerTech12Mo in (1, 0)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

#Personalised asthma action plan (PAAP)
select
	(case TN_ID when 1 then 'Offer in past 12M'
	            when 2 then 'Offer over 12M ago'
	            when 3 then 'No record' end) as Type,

	(case TN_ID when 1 then sum(A2PR_Paap12Mo = 2)
	            when 2 then sum(A2PR_Paap12Mo = 1)
	            when 3 then sum(A2PR_Paap12Mo = 0) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 3 and EVENT_ID = ${EventID}
group by TN_ID;


#Latest asthma control test (ACT) score
select
	(case TN_ID when 1 then 'WITH' when 2 then 'WITHOUT' end) as Review,
	(case TN_ID when 1 then sum(A2PR_ActScore12Mo = 2)
	            when 2 then sum(A2PR_ActScore12Mo in (1, 0)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

select

	(case TN_ID when 1 then '0 - 15 (poor or no asthma control)'
	            when 2 then '16 - 19 (suboptimal asthma control)'
	            when 3 then '20 - 25 (optimal asthma control)' end) as ActScore,

	(case TN_ID when 1 then sum(A2PR_ActValue between 0 and 15)
	            when 2 then sum(A2PR_ActValue between 16 and 19)
	            when 3 then sum(A2PR_ActValue between 20 and 25) end) as Total

from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 3 and EVENT_ID = ${EventID}
group by TN_ID;

#Latest asthma control questionnaire (ACQ) score
select
	(case TN_ID when 1 then 'WITH' when 2 then 'WITHOUT' end) as Review,
	(case TN_ID when 1 then sum(A2PR_AcqScore12m = 2)
	            when 2 then sum(A2PR_AcqScore12m in (1, 0)) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 2 and EVENT_ID = ${EventID}
group by TN_ID;

select

	convert((case TN_ID when 1 then '<0.75 (well-controlled asthma)'
	                    when 2 then '0.75 - 1.49 ("grey zone")'
	                    when 3 then concat(char(14846373),'1.5 (poorly-controlled asthma)') end) using utf8) as ActScore,
	(case TN_ID when 1 then sum(A2PR_AcqScoreValue < 0.75)
	            when 2 then sum(A2PR_AcqScoreValue between 0.75 and 1.49)
	            when 3 then sum(A2PR_AcqScoreValue >= 1.5) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 3 and EVENT_ID = ${EventID}
group by TN_ID;

#Number of SABA prescriptions (past 12 months)
select
	(case TN_ID when 1 then '0 issues'
	            when 2 then '1 - 2 issues'
	            when 3 then '3 - 5 issues'
	            when 4 then '6 - 8 issues'
	            when 5 then '9 - 11 issues'
	            when 6 then '12 or more issues' end) as Issues,

	(case TN_ID when 1 then sum(A2PR_TotalSabaIssues12m = 0)
	            when 2 then sum(A2PR_TotalSabaIssues12m in (1, 2))
	            when 3 then sum(A2PR_TotalSabaIssues12m in (3, 4, 5))
	            when 4 then sum(A2PR_TotalSabaIssues12m in (6, 7, 8))
	            when 5 then sum(A2PR_TotalSabaIssues12m in (9, 10, 11))
	            when 6 then sum(A2PR_TotalSabaIssues12m >= 12) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 6 and EVENT_ID = ${EventID}
group by TN_ID;

#Number of SABA doses/day (past 12 months)*
select
	(case a.TN_ID when 1 then 'less than 1' when 2 then '1 - 2' when 3 then '3 - 4' when 4 then '5 - 6' when 5 then '7 or more' end) as Doses,

	(case b.TN_ID when 1 then 'Current preventer therapy' when 2 then 'No current preventer therapy' end) as Therapy,

	sum((case a.TN_ID when 1 then A2PR_SabaDoseDay between 0 and 0.99
	                  when 2 then A2PR_SabaDoseDay between 1 and 2.99
	                  when 3 then A2PR_SabaDoseDay between 3 and 4.99
	                  when 4 then A2PR_SabaDoseDay between 5 and 6.99
	                  when 5 then A2PR_SabaDoseDay >= 7 end) and
	    (case b.TN_ID when 1 then A2PR_IcsFinal = 1 when 2 then A2PR_IcsFinal = 0 end)) as Total

from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 5 and b.TN_ID <= 2 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;


#12 month analysis of markers of poor asthma control (based on symptoms and/or exacerbations) with respect to SABA issues
select

	convert((case a.TN_ID when 1 then concat(char(14846373),' 2 asthma attacks, or ',char(14846373),' 1 admissions due to asthma (past 12M)')
	                      when 2 then concat(char(14846373),' 2 OCS prescriptions (past 12M)') end) using utf8) as attacks,

	(case b.TN_ID when 1 then '0 issues'
	              when 2 then '1 - 2 issues'
	              when 3 then '3 - 5 issues'
	              when 4 then '6 - 8 issues'
	              when 5 then '9 - 11 issues'
	              when 6 then '12 or more issues' end) as Issues,


	(case a.TN_ID when 1 then (case b.TN_ID when 1 then sum(A2PR_TotalSabaIssues12m = 0 and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m = 0)
	                                        when 2 then sum(A2PR_TotalSabaIssues12m in (1, 2) and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m in (1, 2))
	                                        when 3 then sum(A2PR_TotalSabaIssues12m in (3, 4, 5) and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m in (3, 4, 5))
	                                        when 4 then sum(A2PR_TotalSabaIssues12m in (6, 7, 8) and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m in (6, 7, 8))
	                                        when 5 then sum(A2PR_TotalSabaIssues12m in (9, 10, 11) and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m in (9, 10, 11))
	                                        when 6 then sum(A2PR_TotalSabaIssues12m >= 12 and A2PR_CohortQExac = 1) / sum(A2PR_TotalSabaIssues12m >= 12) end)

	              when 2 then (case b.TN_ID when 1 then sum(A2PR_TotalSabaIssues12m = 0 and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m = 0)
	                                        when 2 then sum(A2PR_TotalSabaIssues12m in (1, 2) and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m in (1, 2))
	                                        when 3 then sum(A2PR_TotalSabaIssues12m in (3, 4, 5) and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m in (3, 4, 5))
	                                        when 4 then sum(A2PR_TotalSabaIssues12m in (6, 7, 8) and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m in (6, 7, 8))
	                                        when 5 then sum(A2PR_TotalSabaIssues12m in (9, 10, 11) and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m in (9, 10, 11))
	                                        when 6 then sum(A2PR_TotalSabaIssues12m >= 12 and A2PR_PoSters12m >= 2) / sum(A2PR_TotalSabaIssues12m >= 12) end) end) as total


from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 2 and b.TN_ID <= 6 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

select
	(case TN_ID when 1 then '0 issues'
	            when 2 then '1 - 2 issues'
	            when 3 then '3 - 5 issues'
	            when 4 then '6 - 8 issues'
	            when 5 then '9 - 11 issues'
	            when 6 then '12 or more issues' end) as Issues,

	(case TN_ID when 1 then sum(A2PR_TotalSabaIssues12m = 0)
	            when 2 then sum(A2PR_TotalSabaIssues12m in (1, 2))
	            when 3 then sum(A2PR_TotalSabaIssues12m in (3, 4, 5))
	            when 4 then sum(A2PR_TotalSabaIssues12m in (6, 7, 8))
	            when 5 then sum(A2PR_TotalSabaIssues12m in (9, 10, 11))
	            when 6 then sum(A2PR_TotalSabaIssues12m >= 12) end) as Total
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers
where TN_ID <= 6 and EVENT_ID = ${EventID}
group by TN_ID;

#Assessment of current asthma management (all patients on the asthma register)
select
	(case a.TN_ID when 1 then 'Asthma' end) as Diag,

	(case b.TN_ID when 1 then 'No current therapy'
	              when 2 then 'SABD only (SABA/SAMA)'
	              when 3 then 'LABD only (LABA/LAMA)'
	              when 4 then 'Other therapies (LTRA/xanthine)'
	              when 5 then 'ICS monotherapy'
	              when 6 then 'ICS + add-on therapies (LABA/LTRA)'
	              when 7 then 'ICS + specialist therapies (LAMA/xanthine/mAb)' end) as Type,

		sum((case b.TN_ID when 1 then A2PR_AstTherapyFinal = 1

		                 when 2 then A2PR_AstTherapyFinal in (2,3,4)

		                 when 3 then A2PR_AstTherapyFinal in (5,6,8,9,10,23,24,26,27,28,41,42,44,45,46,59,60,62,63,64)

		                 when 4 then A2PR_AstTherapyFinal in (19,20,21,22,37,38,39,40,55,56,57,58)

		                 when 5 then A2PR_AstTherapyFinal = 7

		                 when 6 then A2PR_AstTherapyFinal in (11,12,25,29,30)

		                 when 7 then A2PR_AstTherapyFinal in (13,14,15,16,17,18,31,32,33,34,35,36,43,47,48,49,50,51,52,53,54,61,65,66,67,68,69,70,71,72)

		                 end) and (case a.TN_ID when 1 then A2PR_AstCopdAd = 1 end)) as total

from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers as a
join tbl_Numbers as b
where a.TN_ID <= 1 and b.TN_ID <= 8 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Breakdown of patients with asthma identified with respect to age and concurrent COPD
select
	(case a.TN_ID when 1 then 'Adults with asthma'
	                      when 2 then 'Adults with asthma + COPD'
	                      when 3 then 'Aged < 18 with asthma' end) as Type,

	(case b.TN_ID
		when 1 then 'Patients'
		 end) as cohort,

	(case b.TN_ID when 1 then (case a.TN_ID when 1 then sum(A2PR_Age >= 18 and A2PR_Cohort1 = 1 and A2PR_PatientCohort = 1 and A2PR_AstCopdAd = 1)
	                                        when 2 then sum(A2PR_Age >= 18 and A2PR_Cohort1 = 1 and A2PR_PatientCohort = 1 and A2PR_AstCopdAd = 2)
	                                        when 3 then sum(A2PR_Age < 18 and A2PR_Cohort1 = 1 and A2PR_PatientCohort = 1) end) end) as Total


from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers a
join tbl_Numbers b
where a.TN_ID <= 3 and b.TN_ID <= 1 and EVENT_ID = ${EventID}
group by a.TN_ID, b.TN_ID;

#Assessment of pharmacological management with respect to identified cohort (excluding patients with asthma aged < 18)
select
	convert((case a.TN_ID when 1 then concat('No current therapy (n = ',sum(A2PR_AstTherapyFinal = 1 and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2)),')')
	            when 2 then concat('SABD only (SABA/SAMA) (n = ', sum(A2PR_AstTherapyFinal in (2, 3, 4) and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2))  ,     ')')
	            when 3 then concat('LABD only (LABA/LAMA) (n = ', sum(   A2PR_AstTherapyFinal in (5, 6, 8, 9, 10, 23, 24, 26, 27, 28, 41, 42, 44, 45, 46, 59, 60, 62, 63, 64) and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2))   ,')')
	            when 4 then concat('Other therapies (LTRA/xanthine) (n = ', sum(  A2PR_AstTherapyFinal in (19, 20, 21, 22, 37, 38, 39, 40, 55, 56, 57, 58) and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2) )    ,')')
	            when 5 then concat('ICS monotherapy (n = ',   sum( A2PR_AstTherapyFinal = 7 and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2)  )       ,')')
	            when 6 then concat('ICS + add-on therapies (LABA/LTRA) (n = ',  sum( A2PR_AstTherapyFinal in (11, 12, 25, 29, 30) and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2) )       ,')')
	            when 7 then concat('ICS + specialist therapies (LAMA/xanthine/mAb) (n = ',   sum( A2PR_AstTherapyFinal in (13, 14, 15, 16, 17, 18, 31, 32, 33, 34, 35, 36, 43, 47, 48, 49, 50, 51,
	            52, 53, 54, 61, 65, 66, 67, 68, 69, 70, 71, 72) and (A2PR_PatientCohort = 1 or A2PR_PatientCohort = 2))         ,')') end)using utf8) as Type,

	(case b.TN_ID when 1 then 'Patients'

		end) as Total,
	(case b.TN_ID when 1 then (case a.TN_ID when 1 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal = 1)
	                                        when 2 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (2, 3, 4))
	                                        when 3 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (5, 6, 8, 9, 10, 23, 24, 26, 27, 28, 41, 42, 44, 45, 46, 59, 60, 62, 63, 64))
	                                        when 4 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (19, 20, 21, 22, 37, 38, 39, 40, 55, 56, 57, 58))
	                                        when 5 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (7))
	                                        when 6 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (11, 12, 25, 29, 30))
	                                        when 7 then sum(A2PR_PatientCohort = 1 and A2PR_AstTherapyFinal in (13, 14, 15, 16, 17, 18, 31, 32, 33, 34, 35, 36, 43, 47, 48, 49, 50, 51,
	            52, 53, 54, 61, 65, 66, 67, 68, 69, 70, 71, 72)) end) end) as Value
from DialInAsthma2PatientResults
left join DialIns on DIALIN_ID = A2PR_DialInID
left join Reviews on R_PreDataExtract = DIALIN_ID
left join Events on EVENT_ReviewID = R_ID
join tbl_Numbers a
join tbl_Numbers b
where A2PR_Age >= 18 and a.TN_ID <= 7 and b.TN_ID <= 1 and EVENT_ID = ${EventID}
group by a.TN_ID,b.TN_ID;