import { Component, OnInit, OnDestroy, ElementRef, ViewChild } from '@angular/core';
import { ApiService, Metadata, MetadataPayload, TalentManagerPanelData } from '../../../services/api.service';


class CSVGenerationForm {
  businessUnit: string;
}

class CSVUploadForm {
  populationFile: string;
}

@Component({
  selector: 'app-talent-manager-panel',
  templateUrl: './talent-manager-panel.component.html',
  styleUrls: ['./talent-manager-panel.component.scss']
})
export class TalentManagerPanelComponent implements OnInit, OnDestroy {

  successMsg: string;
  errorMsg: string;
  data: TalentManagerPanelData;
  csvDataToUpload: string;
  csvUploadSubmitting: boolean = false;
  metadata: Metadata;
  csvGenerationForm: CSVGenerationForm = {'businessUnit': ''};
  csvUploadForm: CSVUploadForm = {'populationFile': ''};
  csvGenerationSubmitting: boolean = false;
  @ViewChild('inputFile') private inputFile: ElementRef;


  // button text and template key is aligned with feedback_tool/constants.py
  public reminderButtonInfo = [
    {'text': 'Send "Opportunity to Enrol Reminder" email to all employees not yet enrolled', 'templateKey': 'enrol_reminder'},
    {'text': 'Send "Provide Feedback Reminder" email to all employees', 'templateKey': 'entry_reminder'},
    {'text': 'Send "Manager Review and Schedule Feedback Discussions Reminder" email to all managers',
    'templateKey': 'approve_reminder'},
  ];

  public initialButtonInfo = [
    {'text': 'Send "Opportunity to Enrol" email to all employees', 'templateKey': 'enrol_start'},
    {'text': 'Send "Provide Feedback" email to all employees', 'templateKey': 'entry_start'},
    {'text': 'Send "Manager Review and Schedule Feedback Discussions" email to all managers', 'templateKey': 'approve_start'},
    {'text': 'Send "Your feedback is available" email to enrolled employees who have summarised feedback',
    'templateKey': 'review_start'},
  ];

  constructor(public api: ApiService) { }

  ngOnInit() {
    this.updatePageData();
    this.api.getMetadata().subscribe(
      (result: MetadataPayload) => {
        this.metadata = result.metadata;
      },
    );
  }

  updatePageData() {
    this.api.getTalentManagerPageData().subscribe((payload) => {
      this.data = payload;
    });
  }

  ngOnDestroy() {
    this.successMsg = null;
    this.errorMsg = null;
  }

  onClick(event, templateKey: string) {
    event.target.disabled = true;
    this.api.sendEmail(templateKey).subscribe(() => {
      this.successMsg = 'Emails successfully sent!';
      event.target.disabled = false;
    }, () => {
      this.errorMsg = `Emails failed to send. Please email ${this.metadata.supportEmail} to look at backend logs.`;
      event.target.disabled = false;
    });
  }

  onFileChange(event) {
    let reader = new FileReader();
    if (event.target.files && event.target.files.length > 0) {
      let file = event.target.files[0];
      reader.readAsDataURL(file);
      reader.onload = () => {
        this.csvDataToUpload = String(reader.result).split(',')[1];
      }
    }
  }

  onUploadNewPopulationCSV(form) {
    this.successMsg = null;
    this.errorMsg = null;
    this.csvUploadSubmitting = true;
    this.api.uploadNewPopulationCSV(this.csvDataToUpload)
      .subscribe((payload) => {
        let htmlMessage = '<ul>';
        for (let message of payload.messages) {
            htmlMessage += `<li>${message}</li>\n`;
        }
        htmlMessage += '</ul>';
        this.successMsg = '<p>Completed with the following messages:</p> ' + htmlMessage;
        this.updatePageData();
        this.csvUploadSubmitting = false;
        this.inputFile.nativeElement.value = '';
      }, (error) => {
        this.errorMsg = error.error ? error.error.message : error.message;
        this.csvUploadSubmitting = false;
        this.inputFile.nativeElement.value = '';
      })
  }

  onGeneratePopulationCSV(form) {
    this.successMsg = null;
    this.errorMsg = null;
    this.csvGenerationSubmitting = true;
    this.api.generatePopulationCSV(form.value.businessUnit)
      .subscribe((content) => {
        if (content) {
          var blob = new Blob([content], { type: 'text/csv' });
          var url = window.URL.createObjectURL(blob);
          let anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = `${form.value.businessUnit}.csv`;
          anchor.dataset.downloadurl = ['text/plain', anchor.download, anchor.href].join(':');
          anchor.click();
          // window.open(url);
        }
        this.csvGenerationSubmitting = false;
      }, (error) => {
        this.errorMsg = error.error ? error.error.message : error.message;
        this.csvGenerationSubmitting = false;
      })
  }
}
