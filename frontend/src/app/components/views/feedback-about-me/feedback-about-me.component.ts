import { Component, OnInit } from '@angular/core';
import { ApiService, FeedbackHistoryPayload } from '../../../services/api.service';

@Component({
  selector: 'app-feedback-about-me',
  templateUrl: './feedback-about-me.component.html',
  styleUrls: ['./feedback-about-me.component.scss']
})
export class FeedbackAboutMeComponent implements OnInit {

  data: FeedbackHistoryPayload | {};
  constructor(public api: ApiService) { }

  readonly title = 'Review my feedback';
  readonly description = [`Find below a summary of your feedback. Your colleagues were given the opportunity to provide feedback. \
    Your Line Manager then reviewed the feedback and provided the summary presented below.`,
    `Managers can view historical feedback about their Direct Reports spanning the last three feedback cycles. \
    Staff can see their full history of feedback.`,
    `If you would like to discuss your feedback you should reach out to either your Line Manager or your Talent Manager.`];

  ngOnInit() {
    this.api.getFeedbackAboutMe().subscribe(data => {
      this.data = data;
    });
  }

}
