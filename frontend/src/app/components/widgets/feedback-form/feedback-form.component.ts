import { Component, Input, Output, EventEmitter, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { SummaryFeedbackPayload, FeedbackForm } from '../../../services/api.service';

export enum FormState {
  Editing,
  Submitting,
  Success,
}

@Component({
  selector: 'app-feedback-form',
  templateUrl: './feedback-form.component.html',
  styleUrls: ['./feedback-form.component.scss']
})
export class FeedbackFormComponent {

  public formStates = FormState;
  @Input() form: FeedbackForm;
  @Input() public formState: FormState;
  @Input() public successButtonLink: string;
  @Input() public formInfo: string;
  @Input() public saveCaption: string;
  @Input() public successTitle: string;
  @Input() public successInfo: string;
  @Input() public successButton: string;

  @Output() submitRequest = new EventEmitter<NgForm>();
  @ViewChild('f') templateForm: NgForm;

  username: String;

  onSubmit(form: NgForm) {
    this.submitRequest.emit(form);
  }
}
