import { Component, OnInit, ViewChild, HostListener } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, SummaryFeedbackPayload, FeedbackForm } from '../../../services/api.service';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { FormState } from '../../../components/widgets/feedback-form/feedback-form.component';
import { ComponentCanDeactivate } from '../../../guards/pending-changes-guard.service';
import { FeedbackFormComponent } from '../../widgets';

@Component({
  selector: 'app-summarise-feedback',
  templateUrl: './summarise-feedback.component.html',
  styleUrls: ['./summarise-feedback.component.scss']
})
export class SummariseFeedbackComponent implements OnInit {

  public formStates = FormState;
  form: FeedbackForm;
  username: String;
  formState: FormState = FormState.Editing;
  successButtonLink = '/team-feedback';
  @ViewChild('formComponent') formComponent: FeedbackFormComponent;

  readonly formInfo = `<p>For each question, please review, edit & summarize the feedback that has been given:</p>
    <ul>
      <li>The raw contributions are in the first box which is greyed out</li>
      <li>Please enter your summary into the second box, which has been prefilled with the raw contributions.</li>
    </ul>`;

  readonly successTitle = 'Summary successfully saved!';
  readonly successButton = 'Back to team stats page';

  constructor(public api: ApiService, private route: ActivatedRoute) { }

  @HostListener('window:beforeunload')
  canDeactivate(): boolean {
    if (this.formComponent.templateForm) {
      return !this.formComponent.templateForm.dirty;
    } else {
      return true;
    }
  }

  ngOnInit() {
    this.fetchData();
  }

  successInfo(): string {
      if (this.form) {
          return `Thank you for taking the time to summarise feedback on ${this.form.employee.displayName}.
              You should complete all feedback summaries by ${this.form.endDate}. Failure to meet this deadline
              will result in your remaining direct reports receiving no feedback from their colleagues.`;
      }
  }

  saveCaption(): string {
    if (this.form) {
      return `Please kindly double check your summary before proceeding: once you hit the Save button,
        your feedback will be saved and available for editing until the end of the "Review feedback" period at ${this.form.endDate}.
        After this time, it will be automatically released to your direct report(s).` ;
    }
  }

  fetchData() {
    this.route.params.pipe(map(p => p.username)).subscribe((username: String) => {
      this.username = username;
      this.api.getSummaryFeedback(username).subscribe((data: SummaryFeedbackPayload) => {
        this.form = data.summary;
      });
    });
  }

  onSubmit(form: NgForm) {
    this.formState = FormState.Submitting;
    this.api.putSummaryFeedback(this.username, this.form.items).subscribe((isSuccess: any) => {
      this.formState = FormState.Success;
    },
      err => {
        this.formState = FormState.Editing;
        console.log('Request to PUT form failed');
        throw err;
      });
  }
}
