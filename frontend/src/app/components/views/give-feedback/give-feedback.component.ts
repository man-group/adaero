import { Component, Input, OnInit, HostListener, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, Subscribable } from 'rxjs';
import { map } from 'rxjs/operators';

import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ApiService, GiveFeedbackPayload, FeedbackFormItem, FeedbackForm } from '../../../services/api.service';
import { FeedbackFormComponent, FormState } from '../../widgets';
import { ComponentCanDeactivate } from '../../../guards/pending-changes-guard.service';

@Component({
    selector: 'app-give-feedback',
    templateUrl: './give-feedback.component.html',
    styleUrls: ['./give-feedback.component.scss']
})
export class GiveFeedbackComponent implements ComponentCanDeactivate, OnInit {

    public formStates = FormState;
    form: FeedbackForm;
    username: String;
    formState: FormState = FormState.Editing;
    successButtonLink = '/feedback';
    @ViewChild('formComponent') formComponent: FeedbackFormComponent;

    readonly formInfo = `<p>Thank you for taking the time to provide feedback on one of your colleagues.</p>
    <p>You will be asked to answer some simple questions:</p>
    <ul>
        <li>You should base your responses on your actual experience of working with this colleague.</li>
        <li>Feedback is most useful when you share specific examples, of observed behaviours
        and describe the impact this behaviour had.</li>
        <li>Feedback should motivate, improve performance and support continuous learning.
        Please consider this when providing your input.</li>
    </ul>`;

    readonly successTitle = 'Feedback successfully saved!';
    readonly successButton = 'Give feedback';


    constructor(private api: ApiService, private route: ActivatedRoute, public modal: NgbModal) { }

    ngOnInit() {
        this.fetchData();
    }

    @HostListener('window:beforeunload')
    canDeactivate(): boolean {
        if (this.formComponent.templateForm) {
            return !this.formComponent.templateForm.dirty;
        } else {
            return true;
        }
    }

    successInfo(): string {
        if (this.form) {
            return `Thank you for taking the time to provide feedback on one of your colleagues.
                You can continue to give feedback until ${this.form.endDate}.`;
        }
    }

    saveCaption(): string {
        if (this.form) {
            return `Please kindly double check your feedback before proceeding: once you hit the Save button,
                your feedback will be saved and available for editing until the end of the "Give feedback" period at ${this.form.endDate}.
                After this time, it will automatically be submitted and released to your colleague's manager.` ;
        }
    }

    fetchData() {
        this.route.params.pipe(map(p => p.username)).subscribe((username: String) => {
            this.username = username;
            this.api.getFeedbackForm(username).subscribe((data: GiveFeedbackPayload) => {
                this.form = data.form;
            });
        });
    }

    onSubmit(form: NgForm) {
        this.formState = FormState.Submitting;
        this.api.putFeedbackForm(this.username, this.form.items).subscribe((isSuccess: any) => {
            this.formState = FormState.Success;
        },
            err => {
                this.formState = FormState.Editing;
                console.log('Request for PUT failed');
                throw err;
            });
    }
}
