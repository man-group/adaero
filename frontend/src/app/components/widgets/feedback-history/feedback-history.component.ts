import { Component, OnInit, Input } from '@angular/core';
import { FeedbackHistoryPayload } from '../../../services/api.service';

@Component({
  selector: 'app-feedback-history',
  templateUrl: './feedback-history.component.html',
  styleUrls: ['./feedback-history.component.scss']
})
export class FeedbackHistoryComponent implements OnInit {

  @Input() public data: FeedbackHistoryPayload;
  @Input() public title: string;
  @Input() public description: string;

  constructor() { }

  ngOnInit() {
  }

}
