import { Component, OnInit, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ApiService, ExternalFeedbackStatusPayload, MetadataPayload, Metadata } from '../../../services/api.service';

@Component({
  selector: 'app-external-invite',
  templateUrl: './external-invite.component.html',
  styleUrls: ['./external-invite.component.scss']
})
export class ExternalInviteComponent implements OnInit {

  successMsg: string;
  errorMsg: string;
  metadata: Metadata;
  status: ExternalFeedbackStatusPayload | {};
  constructor(private api: ApiService) { }

  ngOnInit() {
    this.fetchStatus();
    this.api.getMetadata().subscribe(
      (result: MetadataPayload) => {
        this.metadata = result.metadata;
      },
    );
  }

  fetchStatus() {
    this.api.getExternalInviteStatus().subscribe((payload) => {
      this.status = payload;
    });
  }

  onSubmit(form: NgForm) {
    this.successMsg = null;
    this.errorMsg = null;
    this.api.sendExternalInvite(form.value.email).subscribe(() => {
      this.successMsg = 'Invite successfully sent!';
    }, (error) => {
      this.errorMsg = error.error ? error.error.message : error.message;
    });
  }

}
